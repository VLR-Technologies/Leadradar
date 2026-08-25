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


async def test_service_deduplicates_only_exact_source_ids() -> None:
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

    assert [business.source_id for business in result.businesses] == ["node:1", "way:2"]
    assert [business.name for business in result.businesses] == [
        "Alpha Dental",
        "Alpha Dental",
    ]
    assert result.location.country_code == "DE"
