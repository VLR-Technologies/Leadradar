from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RegionDefinition:
    name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CityDefinition:
    name: str
    region: str | None = None
    aliases: tuple[str, ...] = ()
    osm_names: tuple[str, ...] = ()
    boundary_relation_ids: tuple[int, ...] = ()


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

INDIA_CITIES = (
    CityDefinition(
        "Hyderabad",
        region="Telangana",
        boundary_relation_ids=(7255986,),
    ),
    CityDefinition(
        "Bengaluru",
        region="Karnataka",
        aliases=("Bangalore",),
        osm_names=("Bangalore",),
    ),
    CityDefinition("Mumbai", region="Maharashtra", aliases=("Bombay",)),
    CityDefinition("Delhi", region="Delhi", osm_names=("New Delhi",)),
    CityDefinition("Chennai", region="Tamil Nadu", aliases=("Madras",)),
    CityDefinition("Pune", region="Maharashtra"),
    CityDefinition("Kolkata", region="West Bengal", aliases=("Calcutta",)),
    CityDefinition("Ahmedabad", region="Gujarat"),
    CityDefinition("Jaipur", region="Rajasthan"),
    CityDefinition("Kochi", region="Kerala", aliases=("Cochin",)),
    CityDefinition("Gurugram", region="Haryana", aliases=("Gurgaon",)),
    CityDefinition("Noida", region="Uttar Pradesh"),
    CityDefinition(
        "Visakhapatnam",
        region="Andhra Pradesh",
        aliases=("Vizag",),
    ),
    CityDefinition("Coimbatore", region="Tamil Nadu"),
    CityDefinition("Surat", region="Gujarat"),
)

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
