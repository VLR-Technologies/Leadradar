from app.core.categories import BusinessCategory
from app.models.business import Business, BusinessAddress
from app.models.location import ResolvedLocation
from app.services.business_discovery import BusinessDiscoveryService
from app.services.location_resolver import LocationResolver


def make_business(source_id: str, name: str) -> Business:
    return Business(
        source_id=source_id,
        source="openstreetmap",
        name=name,
        category="Dentist",
        address=BusinessAddress(city="Berlin", country="Germany"),
        latitude=None,
        longitude=None,
        phone=None,
        email=None,
        website=None,
        opening_hours=None,
    )


class StubProvider:
    async def discover(
        self,
        *,
        location: ResolvedLocation,
        category: BusinessCategory,
        limit: int,
    ) -> list[Business]:
        return [
            make_business("node:1", "Alpha Dental"),
            make_business("node:1", "Alpha Dental duplicate"),
            make_business("way:2", "Alpha Dental"),
        ]


async def test_service_deduplicates_matching_source_records() -> None:
    service = BusinessDiscoveryService(
        provider=StubProvider(),
        location_resolver=LocationResolver(),
    )

    result = await service.discover(
        country_code="DE",
        region=None,
        city="Berlin",
        category="Dentist",
        limit=100,
    )

    assert [business.source_id for business in result.businesses] == ["node:1"]
    assert result.businesses[0].source_ids == {
        "openstreetmap": ("node:1", "way:2")
    }
    assert result.businesses[0].lead_id is not None
    assert result.location.country_code == "DE"
    assert result.providers[0].status == "success"
