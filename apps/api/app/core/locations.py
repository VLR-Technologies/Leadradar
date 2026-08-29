import json
import math
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from app.models.location import BoundingBox


@dataclass(frozen=True, slots=True)
class RegionDefinition:
    name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CityDefinition:
    name: str
    region: str | None = None
    district: str | None = None
    aliases: tuple[str, ...] = ()
    osm_names: tuple[str, ...] = ()
    boundary_relation_ids: tuple[int, ...] = ()
    bounding_box: BoundingBox | None = None
    geoname_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    population: int = 0
    generated_search_envelope: bool = False


@dataclass(frozen=True, slots=True)
class CountryDefinition:
    code: str
    name: str
    requires_region: bool
    cities: tuple[CityDefinition, ...]
    regions: tuple[RegionDefinition, ...] = field(default_factory=tuple)


GERMANY_CITIES = (
    CityDefinition("Berlin", boundary_relation_ids=(62422,)),
    CityDefinition("Hamburg"),
    CityDefinition("Munich", aliases=("München",), osm_names=("München",)),
    CityDefinition(
        "Frankfurt",
        aliases=("Frankfurt am Main",),
        osm_names=("Frankfurt am Main",),
    ),
    CityDefinition("Cologne", aliases=("Köln",), osm_names=("Köln",)),
    CityDefinition("Stuttgart"),
    CityDefinition("Düsseldorf", aliases=("Dusseldorf",)),
    CityDefinition("Leipzig"),
    CityDefinition("Dortmund"),
    CityDefinition("Dresden"),
    CityDefinition("Hannover", aliases=("Hanover",)),
    CityDefinition("Nuremberg", aliases=("Nürnberg",), osm_names=("Nürnberg",)),
    CityDefinition("Bremen"),
)

UNITED_KINGDOM_CITIES = (
    CityDefinition(
        "London",
        osm_names=("Greater London",),
        boundary_relation_ids=(175342,),
    ),
    CityDefinition("Manchester"),
    CityDefinition("Birmingham"),
    CityDefinition("Liverpool"),
    CityDefinition("Leeds"),
    CityDefinition("Glasgow"),
    CityDefinition("Edinburgh"),
    CityDefinition("Bristol"),
    CityDefinition("Sheffield"),
    CityDefinition("Newcastle upon Tyne", aliases=("Newcastle",)),
    CityDefinition("Nottingham"),
    CityDefinition("Cardiff"),
    CityDefinition("Belfast"),
)

UNITED_STATES_REGIONS = tuple(
    RegionDefinition(name)
    for name in (
        "Alabama",
        "Alaska",
        "Arizona",
        "Arkansas",
        "California",
        "Colorado",
        "Connecticut",
        "Delaware",
        "District of Columbia",
        "Florida",
        "Georgia",
        "Hawaii",
        "Idaho",
        "Illinois",
        "Indiana",
        "Iowa",
        "Kansas",
        "Kentucky",
        "Louisiana",
        "Maine",
        "Maryland",
        "Massachusetts",
        "Michigan",
        "Minnesota",
        "Mississippi",
        "Missouri",
        "Montana",
        "Nebraska",
        "Nevada",
        "New Hampshire",
        "New Jersey",
        "New Mexico",
        "New York",
        "North Carolina",
        "North Dakota",
        "Ohio",
        "Oklahoma",
        "Oregon",
        "Pennsylvania",
        "Rhode Island",
        "South Carolina",
        "South Dakota",
        "Tennessee",
        "Texas",
        "Utah",
        "Vermont",
        "Virginia",
        "Washington",
        "West Virginia",
        "Wisconsin",
        "Wyoming",
    )
)

UNITED_STATES_CITIES = (
    CityDefinition("New York", region="New York", osm_names=("New York City",)),
    CityDefinition("Los Angeles", region="California"),
    CityDefinition("Chicago", region="Illinois"),
    CityDefinition("Houston", region="Texas"),
    CityDefinition("Phoenix", region="Arizona"),
    CityDefinition("Philadelphia", region="Pennsylvania"),
    CityDefinition("San Antonio", region="Texas"),
    CityDefinition("San Diego", region="California"),
    CityDefinition("Dallas", region="Texas"),
    CityDefinition("San Jose", region="California", aliases=("San José",)),
    CityDefinition(
        "San Francisco",
        region="California",
        boundary_relation_ids=(111968,),
    ),
    CityDefinition("Seattle", region="Washington"),
    CityDefinition("Boston", region="Massachusetts"),
    CityDefinition("Miami", region="Florida"),
    CityDefinition("Austin", region="Texas"),
    CityDefinition("Denver", region="Colorado"),
    CityDefinition(
        "Washington",
        region="District of Columbia",
        aliases=("Washington, D.C.", "Washington DC"),
        osm_names=("District of Columbia",),
    ),
)

INDIA_REVIEWED_CITIES = (
    CityDefinition(
        "Hyderabad",
        region="Telangana",
        boundary_relation_ids=(7255986,),
        bounding_box=BoundingBox(78.12, 17.20, 78.70, 17.65),
    ),
    CityDefinition(
        "Bengaluru",
        region="Karnataka",
        aliases=("Bangalore",),
        osm_names=("Bangalore",),
        bounding_box=BoundingBox(77.32, 12.75, 77.82, 13.20),
    ),
    CityDefinition(
        "Mumbai",
        region="Maharashtra",
        aliases=("Bombay",),
        bounding_box=BoundingBox(72.75, 18.88, 73.05, 19.32),
    ),
    CityDefinition(
        "Delhi",
        region="Delhi",
        osm_names=("New Delhi",),
        bounding_box=BoundingBox(76.84, 28.40, 77.35, 28.89),
    ),
    CityDefinition(
        "Chennai",
        region="Tamil Nadu",
        aliases=("Madras",),
        bounding_box=BoundingBox(80.10, 12.85, 80.35, 13.25),
    ),
    CityDefinition(
        "Pune",
        region="Maharashtra",
        bounding_box=BoundingBox(73.66, 18.38, 74.05, 18.70),
    ),
    CityDefinition(
        "Kolkata",
        region="West Bengal",
        aliases=("Calcutta",),
        bounding_box=BoundingBox(88.18, 22.40, 88.55, 22.75),
    ),
    CityDefinition(
        "Ahmedabad",
        region="Gujarat",
        bounding_box=BoundingBox(72.40, 22.90, 72.75, 23.18),
    ),
    CityDefinition(
        "Jaipur",
        region="Rajasthan",
        bounding_box=BoundingBox(75.62, 26.75, 76.05, 27.10),
    ),
    CityDefinition(
        "Kochi",
        region="Kerala",
        aliases=("Cochin",),
        bounding_box=BoundingBox(76.15, 9.80, 76.45, 10.15),
    ),
    CityDefinition(
        "Gurugram",
        region="Haryana",
        aliases=("Gurgaon",),
        bounding_box=BoundingBox(76.80, 28.35, 77.20, 28.62),
    ),
    CityDefinition(
        "Noida",
        region="Uttar Pradesh",
        bounding_box=BoundingBox(77.25, 28.42, 77.55, 28.72),
    ),
    CityDefinition(
        "Visakhapatnam",
        region="Andhra Pradesh",
        aliases=("Vizag",),
        bounding_box=BoundingBox(83.05, 17.55, 83.55, 17.90),
    ),
    CityDefinition(
        "Coimbatore",
        region="Tamil Nadu",
        bounding_box=BoundingBox(76.75, 10.85, 77.20, 11.20),
    ),
    CityDefinition(
        "Surat",
        region="Gujarat",
        bounding_box=BoundingBox(72.65, 21.05, 73.10, 21.35),
    ),
)


def _search_envelope(
    latitude: float,
    longitude: float,
    population: int,
) -> BoundingBox:
    radius_km = (
        30
        if population >= 5_000_000
        else 22
        if population >= 1_000_000
        else 15
        if population >= 250_000
        else 10
        if population >= 50_000
        else 7
    )
    latitude_delta = radius_km / 111.32
    longitude_delta = radius_km / max(20, 111.32 * math.cos(math.radians(latitude)))
    return BoundingBox(
        longitude - longitude_delta,
        latitude - latitude_delta,
        longitude + longitude_delta,
        latitude + latitude_delta,
    )


def _load_india_cities() -> tuple[CityDefinition, ...]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "india_cities.json"
    if not data_path.exists():
        return INDIA_REVIEWED_CITIES
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    rows = payload.get("cities", []) if isinstance(payload, dict) else []
    reviewed = {
        (city.name.casefold(), (city.region or "").casefold()): city
        for city in INDIA_REVIEWED_CITIES
    }
    values: list[CityDefinition] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        region = str(row.get("state") or "").strip() or None
        if not name or not region:
            continue
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        population = int(row.get("population") or 0)
        override = reviewed.get((name.casefold(), region.casefold()))
        aliases = tuple(
            dict.fromkeys(
                (
                    *(override.aliases if override else ()),
                    *(str(value) for value in row.get("aliases", []) if value),
                )
            )
        )
        values.append(
            CityDefinition(
                name=name,
                region=region,
                district=str(row.get("district") or "").strip() or None,
                aliases=aliases,
                osm_names=override.osm_names if override else (),
                boundary_relation_ids=(
                    override.boundary_relation_ids if override else ()
                ),
                bounding_box=(
                    override.bounding_box
                    if override and override.bounding_box
                    else _search_envelope(latitude, longitude, population)
                ),
                geoname_id=int(row["id"]),
                latitude=latitude,
                longitude=longitude,
                population=population,
                generated_search_envelope=not bool(override and override.bounding_box),
            )
        )
    return tuple(values) or INDIA_REVIEWED_CITIES


INDIA_CITIES = _load_india_cities()

COUNTRIES: tuple[CountryDefinition, ...] = (
    CountryDefinition("DE", "Germany", False, GERMANY_CITIES),
    CountryDefinition("GB", "United Kingdom", False, UNITED_KINGDOM_CITIES),
    CountryDefinition(
        "US",
        "United States",
        True,
        UNITED_STATES_CITIES,
        UNITED_STATES_REGIONS,
    ),
    CountryDefinition("IN", "India", False, INDIA_CITIES),
)

_COUNTRIES_BY_CODE = {country.code: country for country in COUNTRIES}


def list_countries() -> tuple[CountryDefinition, ...]:
    return COUNTRIES


def get_country(country_code: str) -> CountryDefinition | None:
    return _COUNTRIES_BY_CODE.get(country_code.strip().upper())


def list_regions(country_code: str) -> tuple[RegionDefinition, ...]:
    country = get_country(country_code)
    return country.regions if country else ()


def list_cities(
    country_code: str,
    region: str | None = None,
) -> tuple[CityDefinition, ...]:
    country = get_country(country_code)
    if country is None:
        return ()
    if not region:
        return country.cities
    region_key = region.strip().casefold()
    return tuple(
        city
        for city in country.cities
        if city.region is not None and city.region.casefold() == region_key
    )


def _search_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(character for character in decomposed if not unicodedata.combining(character)).split()
    )


def search_cities(
    country_code: str,
    query: str,
    *,
    region: str | None = None,
    limit: int = 10,
) -> tuple[CityDefinition, ...]:
    query_key = _search_key(query)
    if not query_key:
        return ()
    ranked: list[tuple[int, int, str, CityDefinition]] = []
    for city in list_cities(country_code, region):
        names = (city.name, *city.aliases)
        normalized_names = tuple(_search_key(value) for value in names)
        context = _search_key(" ".join(value for value in (city.district, city.region) if value))
        if query_key in normalized_names:
            rank = 0
        elif any(value.startswith(query_key) for value in normalized_names):
            rank = 1
        elif any(
            word.startswith(query_key)
            for value in normalized_names
            for word in value.split()
        ):
            rank = 2
        elif any(query_key in value for value in normalized_names) or query_key in context:
            rank = 3
        else:
            continue
        ranked.append((rank, -city.population, city.name.casefold(), city))
    ranked.sort(key=lambda value: value[:3])
    return tuple(value[3] for value in ranked[:limit])
