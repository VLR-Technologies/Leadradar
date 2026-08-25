from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.core.locations import get_country, list_cities, list_countries, list_regions
from app.schemas.location import CityResponse, CountryResponse, RegionResponse

router = APIRouter(prefix="/locations", tags=["locations"])


def _country_or_error(country_code: str):
    country = get_country(country_code)
    if country is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Country is not available in this release: {country_code.upper()}",
        )
    return country


@router.get("/countries", response_model=list[CountryResponse])
async def get_countries() -> list[CountryResponse]:
    return [
        CountryResponse(
            code=country.code,
            name=country.name,
            requires_region=country.requires_region,
        )
        for country in list_countries()
    ]


@router.get("/regions", response_model=list[RegionResponse])
async def get_regions(
    country_code: Annotated[
        str,
        Query(alias="countryCode", min_length=2, max_length=2),
    ],
) -> list[RegionResponse]:
    _country_or_error(country_code)
    return [
        RegionResponse(name=region.name)
        for region in list_regions(country_code)
    ]


@router.get("/cities", response_model=list[CityResponse])
async def get_cities(
    country_code: Annotated[
        str,
        Query(alias="countryCode", min_length=2, max_length=2),
    ],
    region: Annotated[str | None, Query(max_length=120)] = None,
) -> list[CityResponse]:
    country = _country_or_error(country_code)
    if region and country.requires_region:
        known_regions = {item.name.casefold() for item in country.regions}
        if region.casefold() not in known_regions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported region for {country.name}: {region}",
            )
    return [
        CityResponse(name=city.name, region=city.region)
        for city in list_cities(country_code, region)
    ]
