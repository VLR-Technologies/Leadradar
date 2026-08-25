from app.core.categories import get_category


def test_category_to_osm_tag_mapping() -> None:
    dentist = get_category("Dentist")
    clinic = get_category("doctor-clinic")
    hotel = get_category("Hotel")

    assert dentist is not None
    assert [(item.key, item.value) for item in dentist.osm_filters] == [
        ("amenity", "dentist")
    ]
    assert clinic is not None
    assert {(item.key, item.value) for item in clinic.osm_filters} == {
        ("amenity", "doctors"),
        ("amenity", "clinic"),
    }
    assert hotel is not None
    assert [(item.key, item.value) for item in hotel.osm_filters] == [
        ("tourism", "hotel")
    ]


def test_category_lookup_is_case_insensitive() -> None:
    assert get_category("dentist") == get_category("DENTIST")

