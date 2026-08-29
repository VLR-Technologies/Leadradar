import pytest

from app.core.categories import BusinessCategory
from app.models.business import Business, BusinessAddress
from app.models.location import ResolvedLocation
from app.providers.base import AllProvidersFailedError, ProviderTimeoutError
from app.services.business_discovery import BusinessDiscoveryService
from app.services.location_resolver import LocationResolver


def lead() -> Business:
    return Business(
        source_id="overture:1",
        source="overture",
        name="ABC Dental",
        category="Dentist",
        address=BusinessAddress(city="Hyderabad", country="India"),
        latitude=17.4,
        longitude=78.4,
        phone="9876543210",
        email=None,
        website=None,
        opening_hours=None,
        phones=("9876543210",),
        sources=("overture",),
        source_ids={"overture": ("overture:1",)},
        operating_status="open",
    )


class SuccessfulProvider:
    name = "overture"
    display_name = "Overture Maps"

    async def discover(
        self, *, location: ResolvedLocation, category: BusinessCategory, limit: int
    ) -> list[Business]:
        return [lead()]


class TimeoutProvider:
    name = "openstreetmap"
    display_name = "OpenStreetMap"

    async def discover(self, **kwargs):
        raise ProviderTimeoutError


class SlowProvider:
    name = "openstreetmap"
    display_name = "OpenStreetMap"
    overall_timeout_seconds = 0.01

    async def discover(self, **kwargs):
        import asyncio

        await asyncio.sleep(1)
        return []


@pytest.mark.asyncio
async def test_partial_provider_failure_keeps_useful_results() -> None:
    service = BusinessDiscoveryService(
        providers=(SuccessfulProvider(), TimeoutProvider()),
        location_resolver=LocationResolver(),
    )

    result = await service.discover(
        country_code="IN", region=None, city="Hyderabad", category="Dentist", limit=100
    )

    assert len(result.businesses) == 1
    assert [status.status for status in result.providers] == ["success", "timeout"]
    assert result.warnings == (
        "OpenStreetMap timed out, but 1 business was returned from Overture Maps.",
    )
    assert result.businesses[0].opportunity_level == "High"


@pytest.mark.asyncio
async def test_all_provider_failures_raise_typed_error() -> None:
    service = BusinessDiscoveryService(
        providers=(TimeoutProvider(),),
        location_resolver=LocationResolver(),
    )
    with pytest.raises(AllProvidersFailedError):
        await service.discover(
            country_code="IN",
            region=None,
            city="Hyderabad",
            category="Dentist",
            limit=10,
        )


@pytest.mark.asyncio
async def test_orchestrator_enforces_provider_overall_timeout() -> None:
    service = BusinessDiscoveryService(
        providers=(SuccessfulProvider(), SlowProvider()),
        location_resolver=LocationResolver(),
    )

    result = await service.discover(
        country_code="IN", region=None, city="Hyderabad", category="Dentist", limit=10
    )

    assert [status.status for status in result.providers] == ["success", "timeout"]
