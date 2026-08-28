from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel


class FieldProvenanceResponse(ApiModel):
    value: str
    source: Literal["overture", "openstreetmap", "official_website", "search_provider"]
    confidence: Literal["high", "medium", "low"]
    source_url: str | None = None
    source_type: str | None = None


class WebsiteAuditResponse(ApiModel):
    reachable: bool | None = None
    uses_https: bool | None = None
    redirect_behavior: str | None = None
    mobile_viewport: bool | None = None
    contact_page_present: bool | None = None
    email_present: bool | None = None
    phone_present: bool | None = None
    social_links_present: bool | None = None
    title_present: bool | None = None
    meta_description_present: bool | None = None
    broken_response_count: int = 0
    label: str = "Not audited"


class BusinessAddressResponse(ApiModel):
    street: str | None = None
    house_number: str | None = None
    postcode: str | None = None
    locality: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    formatted: str | None = None


class BusinessResponse(ApiModel):
    source_id: str
    source: Literal["overture", "openstreetmap"]
    name: str
    category: str | None
    address: BusinessAddressResponse
    latitude: float | None
    longitude: float | None
    phone: str | None
    email: str | None
    website: str | None
    opening_hours: str | None
    lead_id: str | None = None
    subcategories: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    normalized_phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    websites: list[str] = Field(default_factory=list)
    website_status: Literal[
        "not_found", "candidate", "listed", "verified", "unreachable", "mismatch", "unknown"
    ] = "not_found"
    website_type: Literal[
        "official", "directory", "social", "candidate", "unknown", "none"
    ] = "none"
    directory_links: list[str] = Field(default_factory=list)
    social_links: list[str] = Field(default_factory=list)
    whatsapp_number: str | None = None
    whatsapp_numbers: list[str] = Field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    rating_source: str | None = None
    confidence: float | None = None
    sources: list[Literal["overture", "openstreetmap"]] = Field(default_factory=list)
    source_ids: dict[str, list[str]] = Field(default_factory=dict)
    field_provenance: dict[str, list[FieldProvenanceResponse]] = Field(
        default_factory=dict
    )
    enrichment_status: Literal[
        "not_started", "in_progress", "completed", "partial", "no_data", "failed"
    ] = "not_started"
    website_audit: WebsiteAuditResponse | None = None
    lead_score: int = Field(default=0, ge=0, le=100)
    opportunity_level: Literal["High", "Medium", "Low"] = "Low"
    opportunity_reasons: list[str] = Field(default_factory=list)
    operating_status: str | None = None
    scraped_at: datetime | None = None

