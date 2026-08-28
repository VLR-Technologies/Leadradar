import pytest

from app.core.locations import get_country, list_cities, search_cities
from app.services.location_resolver import (
    CityRegionMismatchError,
    LocationResolver,
    RegionRequiredError,
    UnsupportedCountryError,
)


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("DE", "Germany"),
        ("GB", "United Kingdom"),
        ("US", "United States"),
        ("IN", "India"),
    ],
)
def test_supported_countries(code: str, name: str) -> None:
    country = get_country(code)

    assert country is not None
    assert country.name == name


def test_unsupported_country_is_rejected() -> None:
    with pytest.raises(UnsupportedCountryError):
        LocationResolver().resolve(country_code="ZZ", city="Nowhere")


@pytest.mark.parametrize(
    ("country_code", "region", "city", "expected_country", "expected_city"),
    [
        ("DE", None, "Berlin", "Germany", "Berlin"),
        ("GB", None, "London", "United Kingdom", "London"),
        ("US", "California", "San Francisco", "United States", "San Francisco"),
        ("IN", None, "Hyderabad", "India", "Hyderabad"),
    ],
)
def test_required_location_combinations_resolve(
    country_code: str,
    region: str | None,
    city: str,
    expected_country: str,
    expected_city: str,
) -> None:
    location = LocationResolver().resolve(
        country_code=country_code,
        region=region,
        city=city,
    )

    assert location.country == expected_country
    assert location.city == expected_city


@pytest.mark.parametrize(
    ("country_code", "region", "city", "relation_id"),
    [
        ("DE", None, "Berlin", 62422),
        ("GB", None, "London", 175342),
        ("US", "California", "San Francisco", 111968),
        ("IN", None, "Hyderabad", 7255986),
    ],
)
def test_known_good_cities_use_verified_boundary_ids(
    country_code: str,
    region: str | None,
    city: str,
    relation_id: int,
) -> None:
    location = LocationResolver().resolve(
        country_code=country_code,
        region=region,
        city=city,
    )

    assert location.boundary_relation_ids == (relation_id,)


def test_us_requires_region() -> None:
    with pytest.raises(RegionRequiredError, match="Region is required"):
        LocationResolver().resolve(country_code="US", city="San Francisco")


@pytest.mark.parametrize(
    ("country_code", "input_city", "expected_city", "expected_osm_name"),
    [
        ("DE", "Munich", "Munich", "München"),
        ("DE", "Cologne", "Cologne", "Köln"),
        ("IN", "Bangalore", "Bengaluru", "Bangalore"),
        ("IN", "Bombay", "Mumbai", "Bombay"),
    ],
)
def test_city_aliases_are_centralized(
    country_code: str,
    input_city: str,
    expected_city: str,
    expected_osm_name: str,
) -> None:
    location = LocationResolver().resolve(
        country_code=country_code,
        city=input_city,
    )

    assert location.city == expected_city
    assert expected_osm_name in location.city_query_names


def test_known_us_city_is_rejected_in_wrong_state() -> None:
    with pytest.raises(CityRegionMismatchError, match="California"):
        LocationResolver().resolve(
            country_code="US",
            region="Texas",
            city="San Francisco",
        )


def test_catalogue_does_not_prevent_arbitrary_city_input() -> None:
    location = LocationResolver().resolve(country_code="GB", city="Oxford")

    assert location.city == "Oxford"
    assert location.city_query_names == ("Oxford",)
    assert list_cities("GB")


def test_india_city_search_uses_prefixes_aliases_and_state_context() -> None:
    hyderabad = search_cities("IN", "hyd", limit=5)
    bangalore = search_cities("IN", "Bangalore", limit=5)

    assert hyderabad[0].name == "Hyderabad"
    assert hyderabad[0].region == "Telangana"
    assert bangalore[0].name == "Bengaluru"
    assert bangalore[0].region == "Karnataka"


def test_bundled_india_catalogue_has_broad_coverage_and_generated_envelopes() -> None:
    cities = list_cities("IN")
    warangal = next(city for city in cities if city.name == "Warangal")

    assert len(cities) > 6_000
    assert warangal.bounding_box is not None
    assert warangal.generated_search_envelope is True
