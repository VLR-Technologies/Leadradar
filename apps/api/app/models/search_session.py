from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from app.models.business import Business
from app.models.discovery import ProviderStatus
from app.models.location import ResolvedLocation

SearchFilter = Literal[
    "all",
    "phone",
    "email",
    "official_website",
    "no_official_website",
    "directory_social_only",
    "opportunity_high",
    "opportunity_medium",
    "opportunity_low",
    "enrichment_pending",
    "enrichment_complete",
]


@dataclass(slots=True)
class SearchSession:
    session_id: str
    location: ResolvedLocation
    category: str
    requested_limit: int | Literal["all"]
    effective_limit: int
    businesses: list[Business]
    providers: tuple[ProviderStatus, ...]
    warnings: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    expires_monotonic: float = field(repr=False)


@dataclass(frozen=True, slots=True)
class SearchSessionPage:
    session: SearchSession
    businesses: tuple[Business, ...]
    filter_name: SearchFilter
    page: int
    page_size: int
    total_count: int
    total_pages: int
    summary: dict[str, int]
    enrichment_progress: dict[str, int]
