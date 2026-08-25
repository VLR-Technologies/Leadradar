from dataclasses import dataclass, field
from typing import Literal


ProvenanceSource = Literal["openstreetmap", "official_website", "search_provider"]
Confidence = Literal["high", "medium", "low"]
EnrichmentStatus = Literal[
    "not_started",
    "in_progress",
    "completed",
    "partial",
    "no_data",
    "failed",
]
EnrichmentReasonCode = Literal[
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
]
WebsiteVerificationStatus = Literal[
    "source_listed",
    "verified",
    "unreachable",
    "mismatch",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    value: str
    source: ProvenanceSource
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class EnrichedField:
    primary: FieldProvenance | None = None
    alternatives: tuple[FieldProvenance, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EnrichmentFields:
    phone: EnrichedField = field(default_factory=EnrichedField)
    email: EnrichedField = field(default_factory=EnrichedField)
    website: EnrichedField = field(default_factory=EnrichedField)


@dataclass(frozen=True, slots=True)
class ExtractedContact:
    value: str
    confidence: Confidence
    page_url: str


@dataclass(frozen=True, slots=True)
class WebsiteInspection:
    verification_status: WebsiteVerificationStatus
    final_url: str | None = None
    phones: tuple[ExtractedContact, ...] = field(default_factory=tuple)
    emails: tuple[ExtractedContact, ...] = field(default_factory=tuple)
    visited_pages: tuple[str, ...] = field(default_factory=tuple)
    message: str | None = None


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    url: str
    source: Literal["search_provider"] = "search_provider"
    confidence: Literal["low"] = "low"


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    source_id: str
    status: EnrichmentStatus
    website_status: WebsiteVerificationStatus
    fields: EnrichmentFields
    reason_code: EnrichmentReasonCode | None = None
    message: str | None = None
    visited_pages: tuple[str, ...] = field(default_factory=tuple)
