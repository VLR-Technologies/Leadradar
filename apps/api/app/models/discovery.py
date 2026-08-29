from dataclasses import dataclass
from typing import Literal

from app.models.business import Business
from app.models.location import ResolvedLocation


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider: str
    display_name: str
    status: Literal["success", "failed", "timeout", "skipped"]
    count: int
    duration_ms: int
    message: str | None = None
    accepted_count: int = 0


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    location: ResolvedLocation
    businesses: list[Business]
    providers: tuple[ProviderStatus, ...] = ()
    warnings: tuple[str, ...] = ()
