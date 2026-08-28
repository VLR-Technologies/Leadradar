from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.models.business import Business, BusinessAddress
from app.models.discovery import DiscoveryResult
from app.models.location import ResolvedLocation
from app.models.search_session import SearchFilter
from app.services.search_sessions import (
    SearchSessionNotFoundError,
    SearchSessionStore,
    filter_businesses,
)


def lead(
    index: int,
    *,
    phone: bool = False,
    email: bool = False,
    official: bool = False,
    directory: bool = False,
) -> Business:
    website = f"https://business-{index}.in" if official else None
    return Business(
        source_id=f"overture:{index}",
        source="overture",
        lead_id=f"lead:{index}",
        name=f"Business {index}",
        category="Restaurant",
        address=BusinessAddress(city="Hyderabad", state="Telangana", country="India"),
        latitude=17.4 + index / 10_000,
        longitude=78.4,
        phone=f"+91987654{index:04d}" if phone else None,
        email=f"hello{index}@business.in" if email else None,
        website=website,
        opening_hours=None,
        phones=(f"+91987654{index:04d}",) if phone else (),
        emails=(f"hello{index}@business.in",) if email else (),
        websites=(website,) if website else (),
        website_type="official" if official else "none",
        website_status="listed" if official else "not_found",
        directory_links=(f"https://zomato.com/business-{index}",) if directory else (),
        opportunity_level=("High" if index % 3 == 0 else "Medium"),
    )


def discovery(businesses: list[Business]) -> DiscoveryResult:
    return DiscoveryResult(
        location=ResolvedLocation(
            country_code="IN",
            country="India",
            region="Telangana",
            city="Hyderabad",
            region_query_names=("Telangana",),
            city_query_names=("Hyderabad",),
        ),
        businesses=businesses,
    )


def test_server_side_pagination_filters_and_exact_summary() -> None:
    store = SearchSessionStore()
    session = store.create(
        result=discovery(
            [
                lead(1, phone=True, official=True),
                lead(2, email=True),
                lead(3, phone=True, directory=True),
                lead(4),
            ]
        ),
        category="Restaurant",
        requested_limit=100,
        effective_limit=100,
    )

    first_page = store.page(
        session.session_id,
        page=1,
        page_size=25,
        filter_name="no_official_website",
    )

    assert first_page.total_count == 3
    assert first_page.total_pages == 1
    assert first_page.summary["withPhone"] == 1
    assert first_page.summary["directoryOrSocialOnly"] == 1
    assert first_page.enrichment_progress == {
        "total": 4,
        "processed": 0,
        "pending": 4,
        "failed": 0,
    }


@pytest.mark.parametrize(
    ("filter_name", "expected"),
    [
        ("phone", [1, 3]),
        ("email", [2]),
        ("official_website", [1]),
        ("directory_social_only", [3]),
        ("opportunity_high", [3]),
    ],
)
def test_filter_semantics(filter_name: SearchFilter, expected: list[int]) -> None:
    values = [
        lead(1, phone=True, official=True),
        lead(2, email=True),
        lead(3, phone=True, directory=True),
    ]

    assert [int(value.source_id.split(":")[1]) for value in filter_businesses(values, filter_name)] == expected


def test_sessions_expire_and_return_a_clean_rerun_message() -> None:
    clock = [10.0]
    store = SearchSessionStore(
        ttl_seconds=60,
        time_fn=lambda: clock[0],
        now_fn=lambda: datetime(2026, 8, 29, tzinfo=UTC),
    )
    session = store.create(
        result=discovery([lead(1)]),
        category="Restaurant",
        requested_limit="all",
        effective_limit=2_000,
    )
    clock[0] = 71.0

    with pytest.raises(SearchSessionNotFoundError, match="Run the search again"):
        store.get(session.session_id)


def test_oldest_session_is_evicted_when_bounds_are_reached() -> None:
    store = SearchSessionStore(max_sessions=1, max_records=10)
    first = store.create(
        result=discovery([lead(1)]),
        category="Restaurant",
        requested_limit=100,
        effective_limit=100,
    )
    second = store.create(
        result=discovery([lead(2)]),
        category="Dentist",
        requested_limit=100,
        effective_limit=100,
    )

    with pytest.raises(SearchSessionNotFoundError):
        store.get(first.session_id)
    assert store.get(second.session_id).category == "Dentist"


def test_terminal_enrichment_is_not_selected_again_unless_failed_is_retried() -> None:
    store = SearchSessionStore()
    values = [
        lead(1, phone=True),
        lead(2, phone=True, official=True),
        lead(3),
        replace(lead(4), enrichment_status="completed"),
        replace(lead(5), enrichment_status="failed"),
    ]
    session = store.create(
        result=discovery(values),
        category="Restaurant",
        requested_limit=100,
        effective_limit=100,
    )

    _, candidates = store.enrichment_candidates(
        session.session_id,
        lead_ids=None,
        batch_size=10,
        retry_failed=False,
    )
    _, retried = store.enrichment_candidates(
        session.session_id,
        lead_ids={"lead:5"},
        batch_size=10,
        retry_failed=True,
    )

    assert [value.lead_id for value in candidates] == ["lead:1", "lead:2", "lead:3"]
    assert [value.lead_id for value in retried] == ["lead:5"]
