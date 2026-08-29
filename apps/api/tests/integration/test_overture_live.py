import os

import pytest

from app.core.categories import get_category
from app.providers.discovery.overture import OvertureMapsProvider
from app.services.location_resolver import LocationResolver

pytestmark = pytest.mark.skipif(
    os.getenv("LEADRADAR_RUN_LIVE_TESTS") != "1",
    reason="Set LEADRADAR_RUN_LIVE_TESTS=1 for the controlled public-provider smoke test.",
)


@pytest.mark.asyncio
async def test_hyderabad_dentist_query_returns_a_normalized_place() -> None:
    category = get_category("Dentist")
    assert category is not None
    location = LocationResolver().resolve(country_code="IN", city="Hyderabad")
    results = await OvertureMapsProvider(timeout_seconds=120).discover(
        location=location,
        category=category,
        limit=1,
    )

    assert len(results) == 1
    assert results[0].source == "overture"
    assert results[0].name
    assert results[0].address.city
