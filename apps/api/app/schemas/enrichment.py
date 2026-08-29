from typing import Annotated, Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.business import (
    BusinessResponse,
    FieldProvenanceResponse,
    WebsiteAuditResponse,
)


class EnrichBusinessRequest(ApiModel):
    business: BusinessResponse


class EnrichBusinessesBatchRequest(ApiModel):
    businesses: Annotated[list[BusinessResponse], Field(min_length=1, max_length=20)]


class EnrichedFieldResponse(ApiModel):
    primary: FieldProvenanceResponse | None = None
    alternatives: list[FieldProvenanceResponse] = Field(default_factory=list)


class EnrichmentFieldsResponse(ApiModel):
    phone: EnrichedFieldResponse
    email: EnrichedFieldResponse
    website: EnrichedFieldResponse
    whatsapp: EnrichedFieldResponse = Field(default_factory=EnrichedFieldResponse)


class EnrichBusinessResponse(ApiModel):
    source_id: str
    status: Literal[
        "not_started",
        "in_progress",
        "completed",
        "partial",
        "no_data",
        "failed",
    ]
    website_status: Literal[
        "source_listed",
        "verified",
        "unreachable",
        "mismatch",
        "unknown",
    ]
    fields: EnrichmentFieldsResponse
    reason_code: Literal[
        "ADDITIONAL_CONTACTS_FOUND",
        "PARTIAL_CONTACTS_FOUND",
        "WEBSITE_VERIFIED",
        "SEARCH_PROVIDER_DISABLED",
        "NO_WEBSITE_AVAILABLE",
        "NO_CONTACT_DETAILS_FOUND",
        "WEBSITE_MISMATCH",
        "WEBSITE_TIMEOUT",
        "WEBSITE_UNREACHABLE",
        "WEBSITE_ACCESS_DENIED",
        "DNS_ERROR",
        "INVALID_URL",
        "PARSER_ERROR",
        "PROVIDER_ERROR",
    ] | None = None
    message: str | None = None
    visited_pages: list[str] = Field(default_factory=list)
    social_links: list[str] = Field(default_factory=list)
    directory_links: list[str] = Field(default_factory=list)
    whatsapp_numbers: list[str] = Field(default_factory=list)
    contact_page_url: str | None = None
    website_audit: WebsiteAuditResponse | None = None
    lead_score: int = Field(default=0, ge=0, le=100)
    opportunity_level: Literal["High", "Medium", "Low"] = "Low"
    opportunity_reasons: list[str] = Field(default_factory=list)


class EnrichBusinessesBatchResponse(ApiModel):
    results: list[EnrichBusinessResponse]
