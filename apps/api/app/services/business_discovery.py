import asyncio
import logging
import math
from dataclasses import replace
from time import perf_counter

from app.core.categories import get_category
from app.models.discovery import DiscoveryResult, ProviderStatus
from app.providers.base import (
    AllProvidersFailedError,
    BusinessProvider,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderTimeoutError,
)
from app.services.deduplication import deduplicate_businesses
from app.services.lead_scoring import apply_lead_score
from app.services.location_resolver import LocationResolver

logger = logging.getLogger(__name__)


class UnsupportedCategoryError(ValueError):
    pass


class BusinessDiscoveryService:
    def __init__(
        self,
        *,
        provider: BusinessProvider | None = None,
        providers: tuple[BusinessProvider, ...] | None = None,
        location_resolver: LocationResolver,
        oversample_factor: float = 1.4,
        max_limit: int = 2_000,
    ) -> None:
        configured = providers or ((provider,) if provider else ())
        if not configured:
            raise ValueError("At least one discovery provider is required.")
        self._providers = configured
        self._location_resolver = location_resolver
        self._oversample_factor = oversample_factor
        self._max_limit = max_limit

    async def _run_provider(
        self,
        provider: BusinessProvider,
        *,
        location,
        category,
        limit: int,
    ) -> tuple[list, ProviderStatus]:
        provider_name = getattr(provider, "name", provider.__class__.__name__.casefold())
        display_name = getattr(provider, "display_name", provider.__class__.__name__)
        started = perf_counter()
        logger.info(
            "provider.start",
            extra={"provider": provider_name, "city": location.city, "category": category.id},
        )
        try:
            discovery = provider.discover(
                location=location,
                category=category,
                limit=limit,
            )
            overall_timeout = getattr(provider, "overall_timeout_seconds", None)
            businesses = (
                await asyncio.wait_for(discovery, timeout=overall_timeout)
                if overall_timeout
                else await discovery
            )
            status = "success"
            message = None
        except ProviderNotConfiguredError as exc:
            businesses = []
            status = "skipped"
            message = str(exc)
        except ProviderTimeoutError:
            businesses = []
            status = "timeout"
            message = f"{display_name} timed out."
        except TimeoutError:
            businesses = []
            status = "timeout"
            message = f"{display_name} timed out."
        except ProviderError:
            businesses = []
            status = "failed"
            message = f"{display_name} was unavailable."
        except Exception:
            logger.exception("provider.unexpected_failure", extra={"provider": provider_name})
            businesses = []
            status = "failed"
            message = f"{display_name} was unavailable."
        duration_ms = round((perf_counter() - started) * 1000)
        logger.info(
            "provider.finish",
            extra={
                "provider": provider_name,
                "status": status,
                "count": len(businesses),
                "duration_ms": duration_ms,
            },
        )
        return businesses, ProviderStatus(
            provider=provider_name,
            display_name=display_name,
            status=status,
            count=len(businesses),
            duration_ms=duration_ms,
            message=message,
        )

    async def discover(
        self,
        *,
        country_code: str,
        region: str | None,
        city: str,
        category: str,
        limit: int,
    ) -> DiscoveryResult:
        category_definition = get_category(category)
        if category_definition is None:
            raise UnsupportedCategoryError(f"Unsupported business category: {category}")

        location = self._location_resolver.resolve(
            country_code=country_code,
            region=region,
            city=city,
        )

        outcomes = await asyncio.gather(
            *(
                self._run_provider(
                    provider,
                    location=location,
                    category=category_definition,
                    limit=min(self._max_limit, math.ceil(limit * self._oversample_factor)),
                )
                for provider in self._providers
            )
        )
        statuses = tuple(status for _, status in outcomes)
        if not any(status.status == "success" for status in statuses):
            raise AllProvidersFailedError(
                "No configured business data provider returned a usable response."
            )
        discovered = [business for businesses, _ in outcomes for business in businesses]
        unique_businesses = [
            apply_lead_score(business)
            for business in deduplicate_businesses(discovered)
        ]
        limited_businesses = unique_businesses[:limit]
        statuses = tuple(
            replace(
                provider_status,
                accepted_count=sum(
                    provider_status.provider in (business.sources or (business.source,))
                    for business in limited_businesses
                ),
            )
            for provider_status in statuses
        )
        successful_names = [
            status.display_name for status in statuses if status.status == "success"
        ]
        result_label = "business" if len(unique_businesses) == 1 else "businesses"
        result_verb = "was" if len(unique_businesses) == 1 else "were"
        warnings = tuple(
            f"{status.display_name} {'timed out' if status.status == 'timeout' else 'was unavailable'}, "
            f"but {len(unique_businesses)} {result_label} {result_verb} returned from "
            f"{', '.join(successful_names)}."
            for status in statuses
            if status.status in {"failed", "timeout"}
        )
        return DiscoveryResult(
            location=location,
            businesses=limited_businesses,
            providers=statuses,
            warnings=warnings,
        )
