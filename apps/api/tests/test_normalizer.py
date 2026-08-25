from app.normalizers.osm_business import normalize_osm_business


def test_normalizes_common_osm_variants_and_address() -> None:
    business = normalize_osm_business(
        {
            "type": "way",
            "id": 789123,
            "center": {"lat": 52.5, "lon": 13.4},
            "tags": {
                "name": "Praxis am Park",
                "contact:website": "https://praxis.example",
                "contact:phone": "+49 30 123456",
                "contact:email": "hello@praxis.example",
                "addr:street": "Parkstraße",
                "addr:housenumber": "12A",
                "addr:postcode": "10115",
                "addr:city": "Berlin",
                "addr:state": "Berlin",
                "addr:country": "DE",
                "opening_hours": "Mo-Fr 09:00-17:00",
            },
        },
        category="Dentist",
    )

    assert business.source_id == "way:789123"
    assert business.website == "https://praxis.example"
    assert business.phone == "+49 30 123456"
    assert business.email == "hello@praxis.example"
    assert business.latitude == 52.5
    assert business.longitude == 13.4
    assert business.address.formatted == "Parkstraße 12A, 10115 Berlin, Berlin, DE"
    assert business.opening_hours == "Mo-Fr 09:00-17:00"


def test_missing_website_stays_none() -> None:
    business = normalize_osm_business(
        {"type": "node", "id": 42, "lat": 52.4, "lon": 13.3, "tags": {"name": "A"}},
        category="Dentist",
        fallback_city="Berlin",
        fallback_country="Germany",
    )

    assert business.website is None
    assert business.address.city == "Berlin"
    assert business.address.country == "Germany"


def test_phone_and_email_fallback_variants() -> None:
    business = normalize_osm_business(
        {
            "type": "node",
            "id": 43,
            "tags": {
                "name": "B",
                "contact:mobile": "+49 170 12345",
                "email": "team@example.test",
                "url": "https://example.test",
            },
        },
        category="Consulting",
    )

    assert business.phone == "+49 170 12345"
    assert business.email == "team@example.test"
    assert business.website == "https://example.test"


def test_raw_tags_are_hidden_by_default() -> None:
    business = normalize_osm_business(
        {"type": "node", "id": 44, "tags": {"name": "Private tags"}},
        category="Cafe",
    )

    assert business.raw_tags == {}

