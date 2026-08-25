import httpx
import pytest

from app.core.categories import get_category
from app.models.location import ResolvedLocation
from app.providers.base import LocationResolutionError
from app.providers.overpass import (
    OverpassProvider,
    build_business_query,
    build_city_query,
    build_region_query,
)


def test_query_uses_iso_country_city_aliases_and_limit() -> None:
    category = get_category("Dentist")
    assert category is not None

    location = ResolvedLocation(
        country_code="DE",
        country="Germany",
        region=None,
        city="Munich",
        region_query_names=(),
        city_query_names=("Munich", "München"),
    )
    query = build_city_query(
        location=location,
    )

    assert '["ISO3166-1"="DE"]' in query
    assert '["name"="Munich"]' in query
    assert '["name"="München"]' in query
    assert 'rel(area.country)["boundary"="administrative"]' in query
    assert ".cityBoundary out ids;" in query

    business_query = build_business_query(
        boundaries=[{"type": "relation", "id": 62428}],
        filters=category.osm_filters,
        limit=100,
    )
    assert "rel(id:62428);" in business_query
    assert ".cityBoundary map_to_area->.searchArea;" in business_query
    assert 'nwr["amenity"="dentist"](area.searchArea);' in business_query
    assert business_query.endswith("out center 100;")


@pytest.mark.asyncio
async def test_provider_normalizes_mocked_overpass_response() -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.method == "POST"
        body = await request.aread()
        if request_count == 1:
            assert b"cityBoundary" in body
            return httpx.Response(
                200,
                json={"elements": [{"type": "relation", "id": 62422}]},
            )
        assert b"amenity" in body
        return httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type": "node",
                        "id": 1001,
                        "lat": 52.51,
                        "lon": 13.41,
                        "tags": {"name": "Dental Mitte", "phone": "+49 30 1001"},
                    }
                ]
            },
        )

    category = get_category("Dentist")
    assert category is not None
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OverpassProvider(base_url="https://overpass.test/api", client=client)
        location = ResolvedLocation(
            country_code="DE",
            country="Germany",
            region=None,
            city="Berlin",
            region_query_names=(),
            city_query_names=("Berlin",),
        )
        businesses = await provider.discover(
            location=location,
            category=category,
            limit=10,
        )

    assert len(businesses) == 1
    assert businesses[0].source_id == "node:1001"
    assert businesses[0].address.city == "Berlin"


def test_us_query_resolves_region_before_city() -> None:
    category = get_category("Cafe")
    assert category is not None
    location = ResolvedLocation(
        country_code="US",
        country="United States",
        region="California",
        city="San Francisco",
        region_query_names=("California",),
        city_query_names=("San Francisco",),
    )

    region_query = build_region_query(
        location=location,
    )
    assert 'rel(area.country)["boundary"="administrative"]["name"="California"]' in region_query
    assert ".regionBoundary out ids;" in region_query

    query = build_city_query(
        location=location,
        region_boundaries=[{"type": "relation", "id": 165475}],
    )

    assert "rel(id:165475);" in query
    assert ".regionBoundary map_to_area->.regionArea;" in query
    assert 'rel(area.regionArea)["boundary"="administrative"]["name"="San Francisco"]' in query


def test_extended_query_adds_bounded_place_fallback() -> None:
    category = get_category("Restaurant")
    assert category is not None
    location = ResolvedLocation(
        country_code="IN",
        country="India",
        region=None,
        city="Hyderabad",
        region_query_names=(),
        city_query_names=("Hyderabad",),
    )

    query = build_city_query(
        location=location,
        extended_fallback=True,
    )

    assert 'way(area.country)["boundary"="administrative"]' in query
    assert '["place"~"^(city|town|municipality)$"]' in query


@pytest.mark.asyncio
async def test_provider_rejects_unresolved_location() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"elements": []})

    category = get_category("Restaurant")
    assert category is not None
    location = ResolvedLocation(
        country_code="IN",
        country="India",
        region=None,
        city="Unknown Place",
        region_query_names=(),
        city_query_names=("Unknown Place",),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OverpassProvider(base_url="https://overpass.test/api", client=client)
        with pytest.raises(LocationResolutionError, match="Unknown Place, India"):
            await provider.discover(
                location=location,
                category=category,
                limit=5,
            )


@pytest.mark.asyncio
async def test_provider_retries_rate_limit_once() -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(429)
        if request_count == 2:
            return httpx.Response(
                200,
                json={"elements": [{"type": "relation", "id": 62422}]},
            )
        return httpx.Response(200, json={"elements": []})

    category = get_category("Dentist")
    assert category is not None
    location = ResolvedLocation(
        country_code="DE",
        country="Germany",
        region=None,
        city="Berlin",
        region_query_names=(),
        city_query_names=("Berlin",),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OverpassProvider(
            base_url="https://overpass.test/api",
            client=client,
            rate_limit_retry_seconds=0,
        )
        businesses = await provider.discover(
            location=location,
            category=category,
            limit=5,
        )

    assert request_count == 3
    assert businesses == []
