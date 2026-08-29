from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from app.core.websites import WebsiteType

BusinessSource = Literal["overture", "openstreetmap"]
ProvenanceSource = Literal[
    "overture",
    "openstreetmap",
    "official_website",
    "search_provider",
]
Confidence = Literal["high", "medium", "low"]
WebsiteStatus = Literal[
    "not_found",
    "candidate",
    "listed",
    "verified",
    "unreachable",
    "mismatch",
    "unknown",
]
EnrichmentStatus = Literal[
    "not_started",
    "in_progress",
    "completed",
    "partial",
    "no_data",
    "failed",
]
OpportunityLevel = Literal["High", "Medium", "Low"]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    value: str
    source: ProvenanceSource
    confidence: Confidence
    detail: str | None = None
    source_url: str | None = None
    source_type: str | None = None


@dataclass(frozen=True, slots=True)
class WebsiteAudit:
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


@dataclass(frozen=True, slots=True)
class BusinessAddress:
    street: str | None = None
    house_number: str | None = None
    postcode: str | None = None
    locality: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    formatted: str | None = None


@dataclass(frozen=True, slots=True)
class Business:
    source_id: str
    source: BusinessSource
    name: str
    category: str | None
    address: BusinessAddress
    latitude: float | None
    longitude: float | None
    phone: str | None
    email: str | None
    website: str | None
    opening_hours: str | None
    raw_tags: dict[str, str] = field(default_factory=dict)
    lead_id: str | None = None
    subcategories: tuple[str, ...] = field(default_factory=tuple)
    phones: tuple[str, ...] = field(default_factory=tuple)
    normalized_phones: tuple[str, ...] = field(default_factory=tuple)
    emails: tuple[str, ...] = field(default_factory=tuple)
    websites: tuple[str, ...] = field(default_factory=tuple)
    website_status: WebsiteStatus = "not_found"
    website_type: WebsiteType = "none"
    directory_links: tuple[str, ...] = field(default_factory=tuple)
    social_links: tuple[str, ...] = field(default_factory=tuple)
    whatsapp_number: str | None = None
    whatsapp_numbers: tuple[str, ...] = field(default_factory=tuple)
    rating: float | None = None
    review_count: int | None = None
    rating_source: str | None = None
    confidence: float | None = None
    sources: tuple[BusinessSource, ...] = field(default_factory=tuple)
    source_ids: dict[str, tuple[str, ...]] = field(default_factory=dict)
    field_provenance: dict[str, tuple[FieldProvenance, ...]] = field(
        default_factory=dict
    )
    enrichment_status: EnrichmentStatus = "not_started"
    website_audit: WebsiteAudit | None = None
    lead_score: int = 0
    opportunity_level: OpportunityLevel = "Low"
    opportunity_reasons: tuple[str, ...] = field(default_factory=tuple)
    operating_status: str | None = None
    scraped_at: datetime = field(default_factory=utc_now)

