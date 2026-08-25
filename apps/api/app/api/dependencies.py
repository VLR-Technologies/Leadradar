from functools import lru_cache

from app.core.config import Settings, get_settings
from app.providers.overpass import OverpassProvider
from app.providers.enrichment.search import DisabledBusinessSearchProvider
from app.providers.enrichment.website import WebsiteEnrichmentProvider
from app.services.business_enrichment import BusinessEnrichmentService
from app.services.business_discovery import BusinessDiscoveryService
from app.services.location_resolver import LocationResolver


@lru_cache
def get_discovery_service() -> BusinessDiscoveryService:
    settings: Settings = get_settings()
    provider = OverpassProvider(
        base_url=str(settings.overpass_api_url),
        timeout_seconds=settings.overpass_timeout_seconds,
    )
    return BusinessDiscoveryService(
        provider=provider,
        location_resolver=LocationResolver(),
    )


@lru_cache
def get_enrichment_service() -> BusinessEnrichmentService:
    settings: Settings = get_settings()
    return BusinessEnrichmentService(
        website_provider=WebsiteEnrichmentProvider(
            timeout_seconds=settings.enrichment_http_timeout_seconds,
            max_pages=settings.enrichment_max_pages,
        ),
        search_provider=DisabledBusinessSearchProvider(settings.search_provider),
        batch_limit=settings.enrichment_batch_limit,
        max_concurrency=settings.enrichment_max_concurrency,
    )
