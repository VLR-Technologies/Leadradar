from app.schemas.base import ApiModel


class CountryResponse(ApiModel):
    code: str
    name: str
    requires_region: bool


class RegionResponse(ApiModel):
    name: str


class CityResponse(ApiModel):
    name: str
    region: str | None
