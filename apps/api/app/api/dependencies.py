from functools import lru_cache

from app.core.config import Settings, get_settings
from app.providers.discovery.overture import OvertureMapsProvider
from app.providers.enrichment.search import (
    DisabledBusinessSearchProvider,
    SearxngBusinessSearchProvider,
)
from app.providers.enrichment.website import WebsiteEnrichmentProvider
from app.providers.overpass import OverpassProvider
from app.services.business_discovery import BusinessDiscoveryService
from app.services.call_log import CallLogStore
from app.services.business_enrichment import BusinessEnrichmentService
from app.services.location_resolver import LocationResolver
from app.services.search_sessions import SearchSessionStore
from pathlib import Path


@lru_cache
def get_discovery_service() -> BusinessDiscoveryService:
    settings: Settings = get_settings()
    overture = OvertureMapsProvider(
        enabled=settings.overture_enabled,
        release=settings.overture_release,
        stac_url=str(settings.overture_stac_url),
        timeout_seconds=settings.overture_timeout_seconds,
        extension_directory=settings.overture_duckdb_extension_directory,
    )
    overpass = OverpassProvider(
        base_url=str(settings.overpass_api_url),
        endpoints=settings.overpass_api_urls,
        timeout_seconds=settings.overpass_timeout_seconds,
    )
    return BusinessDiscoveryService(
        providers=(overture, overpass),
        location_resolver=LocationResolver(),
        oversample_factor=settings.discovery_oversample_factor,
        max_limit=settings.discovery_max_limit,
    )


@lru_cache
def get_call_log_store() -> CallLogStore:
    settings: Settings = get_settings()
    return CallLogStore(Path(settings.call_log_db_path))


@lru_cache
def get_search_session_store() -> SearchSessionStore:
    settings: Settings = get_settings()
    return SearchSessionStore(
        ttl_seconds=settings.search_session_ttl_seconds,
        max_sessions=settings.max_active_search_sessions,
        max_records=settings.max_cached_search_records,
    )


@lru_cache
def get_enrichment_service() -> BusinessEnrichmentService:
    settings: Settings = get_settings()
    search_provider = (
        SearxngBusinessSearchProvider(
            base_url=str(settings.searxng_base_url),
            timeout_seconds=settings.enrichment_http_timeout_seconds,
        )
        if settings.searxng_base_url
        else DisabledBusinessSearchProvider(settings.search_provider)
    )
    return BusinessEnrichmentService(
        website_provider=WebsiteEnrichmentProvider(
            timeout_seconds=settings.enrichment_http_timeout_seconds,
            max_pages=settings.enrichment_max_pages,
        ),
        search_provider=search_provider,
        batch_limit=settings.enrichment_batch_limit,
        max_concurrency=settings.enrichment_max_concurrency,
    )
