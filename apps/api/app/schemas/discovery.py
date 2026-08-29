from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.base import ApiModel
from app.schemas.business import BusinessResponse

SearchText = Annotated[str, Field(min_length=1, max_length=120)]
RequestedLimit = Annotated[int, Field(ge=1, le=500)] | Literal["all"]


class DiscoverBusinessesRequest(ApiModel):
    country_code: Annotated[str, Field(min_length=2, max_length=2)]
    region: Annotated[str | None, Field(max_length=120)] = None
    city: SearchText
    category: Annotated[str, Field(min_length=1, max_length=80)]
    limit: RequestedLimit = 100
    page_size: Annotated[int, Field(ge=25, le=100)] = 50

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("region", "city", "category")
    @classmethod
    def validate_search_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        if any(character in cleaned for character in ('"', "{", "}", ";", "\\")):
            raise ValueError("contains unsupported characters")
        if any(ord(character) < 32 for character in cleaned):
            raise ValueError("contains control characters")
        return cleaned


class DiscoveryQueryResponse(ApiModel):
    country_code: str
    country: str
    region: str | None
    city: str
    category: str
    limit: RequestedLimit


class SearchSummaryResponse(ApiModel):
    total: int = 0
    with_phone: int = 0
    with_email: int = 0
    with_official_website: int = 0
    without_official_website: int = 0
    directory_or_social_only: int = 0
    high_opportunity: int = 0
    medium_opportunity: int = 0
    low_opportunity: int = 0


class EnrichmentProgressResponse(ApiModel):
    total: int = 0
    processed: int = 0
    pending: int = 0
    failed: int = 0


class DiscoverBusinessesResponse(ApiModel):
    query: DiscoveryQueryResponse
    count: int
    businesses: list[BusinessResponse]
    providers: list["ProviderStatusResponse"] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    session_id: str
    page: int = 1
    page_size: int
    total_count: int
    total_pages: int
    effective_limit: int
    summary: SearchSummaryResponse
    enrichment_progress: EnrichmentProgressResponse
    expires_at: datetime


class ProviderStatusResponse(ApiModel):
    provider: str
    display_name: str
    status: Literal["success", "failed", "timeout", "skipped"]
    count: int
    duration_ms: int
    message: str | None = None
    accepted_count: int = 0


DiscoverBusinessesResponse.model_rebuild()
