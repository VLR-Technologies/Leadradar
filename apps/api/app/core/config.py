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
    app_version: str = "0.1.0"
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
    search_provider: str = Field(
        default="",
        validation_alias="SEARCH_PROVIDER",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
