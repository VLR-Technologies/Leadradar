from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.core.locations import (
    CityDefinition,
    get_country,
    list_cities,
    list_countries,
    list_regions,
    search_cities,
)
from app.schemas.location import CityResponse, CountryResponse, RegionResponse

router = APIRouter(prefix="/locations", tags=["locations"])


def _city_response(city: CityDefinition) -> CityResponse:
    return CityResponse(
        id=city.geoname_id,
        name=city.name,
        region=city.region,
        district=city.district,
        display_name=", ".join(
            dict.fromkeys(
                value for value in (city.name, city.district, city.region) if value
            )
        ),
        latitude=city.latitude,
        longitude=city.longitude,
        population=city.population,
    )


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
    cities = list_cities(country_code, region)
    if country.code == "IN" and not region:
        cities = cities[:50]
    return [_city_response(city) for city in cities]


@router.get("/cities/search", response_model=list[CityResponse])
async def find_cities(
    country_code: Annotated[
        str,
        Query(alias="countryCode", min_length=2, max_length=2),
    ],
    query: Annotated[str, Query(alias="q", min_length=2, max_length=80)],
    region: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[CityResponse]:
    _country_or_error(country_code)
    return [
        _city_response(city)
        for city in search_cities(
            country_code,
            query,
            region=region,
            limit=limit,
        )
    ]
