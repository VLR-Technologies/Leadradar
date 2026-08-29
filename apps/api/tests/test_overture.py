import json

import httpx
import pytest

from app.core.categories import get_category
from app.providers.discovery.overture import OvertureMapsProvider
from app.services.location_resolver import LocationResolver


@pytest.mark.asyncio
async def test_overture_provider_resolves_latest_and_normalizes_public_fields(tmp_path) -> None:
    captured = {}

    def query_executor(release, bounding_box, categories, limit, extension_directory):
        captured.update(
            release=release,
            bounding_box=bounding_box,
            categories=categories,
            limit=limit,
            extension_directory=extension_directory,
        )
        return [
            {
                "id": "gers-123",
                "names": json.dumps({"primary": "ABC Dental Clinic"}),
                "categories": json.dumps(
                    {"primary": "dentist", "alternate": ["cosmetic_dentist"]}
                ),
                "addresses": json.dumps(
                    [
                        {
                            "freeform": "Road No. 12",
                            "locality": "Hyderabad",
                            "postcode": "500034",
                            "region": "IN-TG",
                            "country": "IN",
                        }
                    ]
                ),
                "phones": json.dumps(["+91 98765 43210"]),
                "websites": json.dumps(["abcdental.in"]),
                "emails": json.dumps(["care@abcdental.in"]),
                "socials": json.dumps(["https://instagram.com/abcdental"]),
                "operating_status": "open",
                "confidence": 0.82,
                "longitude": 78.44,
                "latitude": 17.41,
            }
        ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"latest": "2026-07-22.0"})

    category = get_category("Dentist")
    assert category is not None
    location = LocationResolver().resolve(country_code="IN", city="Hyderabad")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OvertureMapsProvider(
            client=client,
            query_executor=query_executor,
            extension_directory=tmp_path,
        )
        results = await provider.discover(location=location, category=category, limit=100)

    assert captured["release"] == "2026-07-22.0"
    assert captured["bounding_box"] == location.bounding_box
    assert captured["categories"] == ("dentist",)
    assert results[0].source_id == "overture:gers-123"
    assert results[0].phone == "+91 98765 43210"
    assert results[0].normalized_phones == ("+919876543210",)
    assert results[0].address.state == "Telangana"
    assert results[0].address.postcode == "500034"
    assert results[0].website == "https://abcdental.in"
    assert results[0].rating is None
    assert results[0].field_provenance["email"][0].source == "overture"


@pytest.mark.asyncio
async def test_overture_uses_generated_search_envelope_for_bundled_india_city() -> None:
    category = get_category("Dentist")
    assert category is not None
    location = LocationResolver().resolve(country_code="IN", city="Warangal")
    captured = {}

    def query_executor(release, bounding_box, categories, limit, extension_directory):
        captured["bounding_box"] = bounding_box
        return []

    provider = OvertureMapsProvider(
        release="2026-07-22.0",
        query_executor=query_executor,
    )

    assert location.bounding_box is not None
    assert await provider.discover(location=location, category=category, limit=10) == []
    assert captured["bounding_box"] == location.bounding_box
