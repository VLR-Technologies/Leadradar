from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class BusinessAddress:
    street: str | None = None
    house_number: str | None = None
    postcode: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    formatted: str | None = None


@dataclass(frozen=True, slots=True)
class Business:
    source_id: str
    source: Literal["openstreetmap"]
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

