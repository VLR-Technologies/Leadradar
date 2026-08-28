from app.schemas.base import ApiModel


class CountryResponse(ApiModel):
    code: str
    name: str
    requires_region: bool


class RegionResponse(ApiModel):
    name: str


class CityResponse(ApiModel):
    id: int | None = None
    name: str
    region: str | None
    district: str | None = None
    display_name: str
    latitude: float | None = None
    longitude: float | None = None
    population: int = 0
