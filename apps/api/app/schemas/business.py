from typing import Literal

from app.schemas.base import ApiModel


class BusinessAddressResponse(ApiModel):
    street: str | None = None
    house_number: str | None = None
    postcode: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    formatted: str | None = None


class BusinessResponse(ApiModel):
    source_id: str
    source: Literal["openstreetmap"]
    name: str
    category: str | None
    address: BusinessAddressResponse
    latitude: float | None
    longitude: float | None
    phone: str | None
    email: str | None
    website: str | None
    opening_hours: str | None

