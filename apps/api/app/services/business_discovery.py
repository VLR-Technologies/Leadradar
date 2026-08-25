from app.core.categories import get_category
from app.models.discovery import DiscoveryResult
from app.providers.base import BusinessProvider
from app.services.location_resolver import LocationResolver


class UnsupportedCategoryError(ValueError):
    pass


class BusinessDiscoveryService:
    def __init__(
        self,
        *,
        provider: BusinessProvider,
        location_resolver: LocationResolver,
    ) -> None:
        self._provider = provider
        self._location_resolver = location_resolver

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

        businesses = await self._provider.discover(
            location=location,
            category=category_definition,
            limit=limit,
        )

        unique_businesses: list[Business] = []
        seen_source_ids: set[str] = set()
        for business in businesses:
            if business.source_id in seen_source_ids:
                continue
            seen_source_ids.add(business.source_id)
            unique_businesses.append(business)
        return DiscoveryResult(
            location=location,
            businesses=unique_businesses[:limit],
        )
