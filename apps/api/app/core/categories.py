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
    overture_categories: tuple[str, ...] = ()


CATEGORY_CATALOGUE: tuple[BusinessCategory, ...] = (
    BusinessCategory(
        "dentist",
        "Dentist",
        (OsmTagFilter("amenity", "dentist"),),
        ("dentist",),
    ),
    BusinessCategory(
        "dental-clinic",
        "Dental Clinic",
        (OsmTagFilter("amenity", "dentist"),),
        ("dentist", "dental_hygienist"),
    ),
    BusinessCategory(
        "hospital",
        "Hospital",
        (OsmTagFilter("amenity", "hospital"),),
        ("hospital", "childrens_hospital"),
    ),
    BusinessCategory(
        "clinic",
        "Clinic",
        (OsmTagFilter("amenity", "clinic"),),
        ("community_health_center", "storefront_clinic", "doctor"),
    ),
    BusinessCategory(
        "restaurant",
        "Restaurant",
        (
            OsmTagFilter("amenity", "restaurant"),
            OsmTagFilter("amenity", "fast_food"),
            OsmTagFilter("amenity", "food_court"),
        ),
        (
            "restaurant",
            "fast_food_restaurant",
            "food_court",
            "indian_restaurant",
            "vegetarian_restaurant",
        ),
    ),
    BusinessCategory(
        "catering",
        "Catering",
        (OsmTagFilter("craft", "caterer"),),
        ("caterer",),
    ),
    BusinessCategory("cafe", "Cafe", (OsmTagFilter("amenity", "cafe"),), ("cafe",)),
    BusinessCategory(
        "bakery", "Bakery", (OsmTagFilter("shop", "bakery"),), ("bakery",)
    ),
    BusinessCategory(
        "salon",
        "Salon",
        (OsmTagFilter("shop", "hairdresser"),),
        ("hair_salon", "beauty_salon"),
    ),
    BusinessCategory(
        "beauty-parlour",
        "Beauty Parlour",
        (OsmTagFilter("shop", "beauty"),),
        ("beauty_salon",),
    ),
    BusinessCategory(
        "spa", "Spa", (OsmTagFilter("leisure", "spa"),), ("spas", "day_spa")
    ),
    BusinessCategory(
        "gym", "Gym", (OsmTagFilter("leisure", "fitness_centre"),), ("gym",)
    ),
    BusinessCategory(
        "fitness-center",
        "Fitness Center",
        (OsmTagFilter("leisure", "fitness_centre"),),
        ("gym", "sports_and_fitness_instruction"),
    ),
    BusinessCategory("retail-store", "Retail Store", (OsmTagFilter("shop"),), ("retail",)),
    BusinessCategory(
        "clothing-store",
        "Clothing Store",
        (OsmTagFilter("shop", "clothes"),),
        ("clothing_store",),
    ),
    BusinessCategory(
        "jewellery-store",
        "Jewellery Store",
        (OsmTagFilter("shop", "jewelry"),),
        ("jewelry_store",),
    ),
    BusinessCategory("hotel", "Hotel", (OsmTagFilter("tourism", "hotel"),), ("hotel",)),
    BusinessCategory(
        "lodge",
        "Lodge",
        (OsmTagFilter("tourism", "guest_house"), OsmTagFilter("tourism", "chalet")),
        ("lodge", "guest_house"),
    ),
    BusinessCategory(
        "travel-agency",
        "Travel Agency",
        (OsmTagFilter("shop", "travel_agency"),),
        ("travel_agency",),
    ),
    BusinessCategory(
        "real-estate-agency",
        "Real Estate Agency",
        (OsmTagFilter("office", "estate_agent"),),
        ("real_estate_agent", "real_estate_services"),
    ),
    BusinessCategory(
        "interior-designer",
        "Interior Designer",
        (OsmTagFilter("office", "interior_design"),),
        ("interior_design",),
    ),
    BusinessCategory(
        "furniture-store",
        "Furniture Store",
        (OsmTagFilter("shop", "furniture"),),
        ("furniture_store",),
    ),
    BusinessCategory("school", "School", (OsmTagFilter("amenity", "school"),), ("school",)),
    BusinessCategory(
        "coaching-center",
        "Coaching Center",
        (OsmTagFilter("amenity", "training"),),
        ("educational_services", "private_tutor", "specialty_school"),
    ),
    BusinessCategory(
        "preschool",
        "Preschool",
        (OsmTagFilter("amenity", "kindergarten"),),
        ("preschool",),
    ),
    BusinessCategory(
        "automobile-service",
        "Automobile Service",
        (OsmTagFilter("shop", "car_repair"),),
        ("automotive_services_and_repair", "automotive_repair"),
    ),
    BusinessCategory(
        "car-dealer", "Car Dealer", (OsmTagFilter("shop", "car"),), ("car_dealer",)
    ),
    BusinessCategory(
        "electronics-store",
        "Electronics Store",
        (OsmTagFilter("shop", "electronics"),),
        ("electronics", "computer_store", "mobile_phone_store"),
    ),
    BusinessCategory(
        "pharmacy", "Pharmacy", (OsmTagFilter("amenity", "pharmacy"),), ("pharmacy",)
    ),
    BusinessCategory(
        "doctor-clinic",
        "Doctor / Clinic",
        (OsmTagFilter("amenity", "doctors"), OsmTagFilter("amenity", "clinic")),
        ("doctor", "community_health_center"),
    ),
    BusinessCategory(
        "law-firm", "Law Firm", (OsmTagFilter("office", "lawyer"),), ("lawyer",)
    ),
    BusinessCategory(
        "accountant", "Accountant", (OsmTagFilter("office", "accountant"),), ("accountant",)
    ),
    BusinessCategory(
        "consulting", "Consulting", (OsmTagFilter("office", "consulting"),), ("consulting",)
    ),
    BusinessCategory(
        "beauty-salon", "Beauty Salon", (OsmTagFilter("shop", "beauty"),), ("beauty_salon",)
    ),
    BusinessCategory(
        "barber", "Barber", (OsmTagFilter("shop", "hairdresser"),), ("barber",)
    ),
    BusinessCategory(
        "gym-fitness",
        "Gym / Fitness",
        (OsmTagFilter("leisure", "fitness_centre"),),
        ("gym",),
    ),
    BusinessCategory(
        "car-repair",
        "Car Repair",
        (OsmTagFilter("shop", "car_repair"),),
        ("automotive_services_and_repair",),
    ),
    BusinessCategory(
        "construction",
        "Construction",
        (OsmTagFilter("office", "construction"), OsmTagFilter("craft", "builder")),
        ("construction_services",),
    ),
    BusinessCategory(
        "education-training",
        "Education / Training",
        (
            OsmTagFilter("amenity", "training"),
            OsmTagFilter("amenity", "college"),
            OsmTagFilter("office", "educational_institution"),
        ),
        ("educational_services", "specialty_school"),
    ),
)

_CATEGORIES_BY_LABEL = {category.label.casefold(): category for category in CATEGORY_CATALOGUE}
_CATEGORIES_BY_ID = {category.id.casefold(): category for category in CATEGORY_CATALOGUE}


def list_categories() -> tuple[BusinessCategory, ...]:
    return CATEGORY_CATALOGUE


def get_category(value: str) -> BusinessCategory | None:
    key = value.strip().casefold()
    return _CATEGORIES_BY_LABEL.get(key) or _CATEGORIES_BY_ID.get(key)

