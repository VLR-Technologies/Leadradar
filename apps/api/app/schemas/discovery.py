from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.base import ApiModel
from app.schemas.business import BusinessResponse

SearchText = Annotated[str, Field(min_length=1, max_length=120)]


class DiscoverBusinessesRequest(ApiModel):
    country_code: Annotated[str, Field(min_length=2, max_length=2)]
    region: Annotated[str | None, Field(max_length=120)] = None
    city: SearchText
    category: Annotated[str, Field(min_length=1, max_length=80)]
    limit: Annotated[int, Field(ge=1, le=500)] = 100

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("region", "city", "category")
    @classmethod
    def validate_search_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        if any(character in cleaned for character in ('"', "{", "}", ";", "\\")):
            raise ValueError("contains unsupported characters")
        if any(ord(character) < 32 for character in cleaned):
            raise ValueError("contains control characters")
        return cleaned


class DiscoveryQueryResponse(ApiModel):
    country_code: str
    country: str
    region: str | None
    city: str
    category: str
    limit: int


class DiscoverBusinessesResponse(ApiModel):
    query: DiscoveryQueryResponse
    count: int
    businesses: list[BusinessResponse]
