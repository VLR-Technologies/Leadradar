from dataclasses import dataclass

from app.models.business import Business
from app.models.location import ResolvedLocation


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    location: ResolvedLocation
    businesses: list[Business]
