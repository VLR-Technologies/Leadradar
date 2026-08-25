from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OsmTagFilter:
    key: str
    value: str | None = None


@dataclass(frozen=True, slots=True)
class BusinessCategory:
    id: str
    label: str
    osm_filters: tuple[OsmTagFilter, ...]


CATEGORY_CATALOGUE: tuple[BusinessCategory, ...] = (
    BusinessCategory("restaurant", "Restaurant", (OsmTagFilter("amenity", "restaurant"),)),
    BusinessCategory("cafe", "Cafe", (OsmTagFilter("amenity", "cafe"),)),
    BusinessCategory("dentist", "Dentist", (OsmTagFilter("amenity", "dentist"),)),
    BusinessCategory(
        "doctor-clinic",
        "Doctor / Clinic",
        (OsmTagFilter("amenity", "doctors"), OsmTagFilter("amenity", "clinic")),
    ),
    BusinessCategory("law-firm", "Law Firm", (OsmTagFilter("office", "lawyer"),)),
    BusinessCategory("accountant", "Accountant", (OsmTagFilter("office", "accountant"),)),
    BusinessCategory("consulting", "Consulting", (OsmTagFilter("office", "consulting"),)),
    BusinessCategory(
        "real-estate-agency",
        "Real Estate Agency",
        (OsmTagFilter("office", "estate_agent"),),
    ),
    BusinessCategory("hotel", "Hotel", (OsmTagFilter("tourism", "hotel"),)),
    BusinessCategory("beauty-salon", "Beauty Salon", (OsmTagFilter("shop", "beauty"),)),
    BusinessCategory("barber", "Barber", (OsmTagFilter("shop", "hairdresser"),)),
    BusinessCategory(
        "gym-fitness",
        "Gym / Fitness",
        (OsmTagFilter("leisure", "fitness_centre"),),
    ),
    BusinessCategory("car-repair", "Car Repair", (OsmTagFilter("shop", "car_repair"),)),
    BusinessCategory("retail-store", "Retail Store", (OsmTagFilter("shop"),)),
    BusinessCategory(
        "construction",
        "Construction",
        (OsmTagFilter("office", "construction"), OsmTagFilter("craft", "builder")),
    ),
    BusinessCategory(
        "travel-agency",
        "Travel Agency",
        (OsmTagFilter("shop", "travel_agency"),),
    ),
    BusinessCategory(
        "education-training",
        "Education / Training",
        (
            OsmTagFilter("amenity", "training"),
            OsmTagFilter("amenity", "college"),
            OsmTagFilter("office", "educational_institution"),
        ),
    ),
)

_CATEGORIES_BY_LABEL = {category.label.casefold(): category for category in CATEGORY_CATALOGUE}
_CATEGORIES_BY_ID = {category.id.casefold(): category for category in CATEGORY_CATALOGUE}


def list_categories() -> tuple[BusinessCategory, ...]:
    return CATEGORY_CATALOGUE


def get_category(value: str) -> BusinessCategory | None:
    key = value.strip().casefold()
    return _CATEGORIES_BY_LABEL.get(key) or _CATEGORIES_BY_ID.get(key)

