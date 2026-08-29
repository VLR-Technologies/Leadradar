from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Lead Radar API"
    app_version: str = "0.2.0"
    overture_enabled: bool = Field(
        default=True,
        validation_alias="OVERTURE_ENABLED",
    )
    overture_release: str = Field(
        default="latest",
        validation_alias="OVERTURE_RELEASE",
    )
    overture_stac_url: AnyHttpUrl = Field(
        default="https://stac.overturemaps.org/catalog.json",
        validation_alias="OVERTURE_STAC_URL",
    )
    overture_timeout_seconds: float = Field(
        default=45.0,
        ge=10.0,
        le=120.0,
        validation_alias="OVERTURE_TIMEOUT_SECONDS",
    )
    overture_duckdb_extension_directory: str = Field(
        default=".duckdb/extensions",
        validation_alias="OVERTURE_DUCKDB_EXTENSION_DIRECTORY",
    )
    overpass_api_url: AnyHttpUrl = Field(
        default="https://lz4.overpass-api.de/api/interpreter",
        validation_alias="OVERPASS_API_URL",
    )
    overpass_timeout_seconds: float = Field(
        default=35.0,
        ge=5.0,
        le=120.0,
        validation_alias="OVERPASS_TIMEOUT_SECONDS",
    )
    enrichment_http_timeout_seconds: float = Field(
        default=10.0,
        ge=2.0,
        le=30.0,
        validation_alias="ENRICHMENT_HTTP_TIMEOUT_SECONDS",
    )
    enrichment_max_pages: int = Field(
        default=4,
        ge=1,
        le=5,
        validation_alias="ENRICHMENT_MAX_PAGES",
    )
    enrichment_batch_limit: int = Field(
        default=20,
        ge=1,
        le=20,
        validation_alias="ENRICHMENT_BATCH_LIMIT",
    )
    enrichment_max_concurrency: int = Field(
        default=4,
        ge=1,
        le=5,
        validation_alias="ENRICHMENT_MAX_CONCURRENCY",
    )
    discovery_default_limit: int = Field(
        default=100,
        ge=100,
        le=500,
        validation_alias="DISCOVERY_DEFAULT_LIMIT",
    )
    discovery_max_limit: int = Field(
        default=2_000,
        ge=500,
        le=5_000,
        validation_alias="DISCOVERY_MAX_LIMIT",
    )
    discovery_oversample_factor: float = Field(
        default=1.4,
        ge=1.0,
        le=2.0,
        validation_alias="DISCOVERY_OVERSAMPLE_FACTOR",
    )
    search_session_ttl_seconds: int = Field(
        default=1_800,
        ge=60,
        le=7_200,
        validation_alias="SEARCH_SESSION_TTL_SECONDS",
    )
    max_active_search_sessions: int = Field(
        default=20,
        ge=1,
        le=100,
        validation_alias="MAX_ACTIVE_SEARCH_SESSIONS",
    )
    max_cached_search_records: int = Field(
        default=10_000,
        ge=500,
        le=50_000,
        validation_alias="MAX_CACHED_SEARCH_RECORDS",
    )
    default_page_size: int = Field(
        default=50,
        ge=25,
        le=100,
        validation_alias="DEFAULT_PAGE_SIZE",
    )
    max_page_size: int = Field(
        default=100,
        ge=25,
        le=100,
        validation_alias="MAX_PAGE_SIZE",
    )
    search_provider: str = Field(
        default="",
        validation_alias="SEARCH_PROVIDER",
    )
    overpass_api_urls_raw: str = Field(
        default="",
        validation_alias="OVERPASS_API_URLS",
    )
    searxng_base_url: str = Field(
        default="",
        validation_alias="SEARXNG_BASE_URL",
    )
    cors_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def overpass_api_urls(self) -> tuple[str, ...]:
        configured = tuple(
            value.strip().rstrip("/")
            for value in self.overpass_api_urls_raw.split(",")
            if value.strip()
        )
        return configured or (str(self.overpass_api_url),)


@lru_cache
def get_settings() -> Settings:
    return Settings()
