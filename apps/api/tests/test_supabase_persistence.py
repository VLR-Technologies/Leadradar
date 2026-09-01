from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.api.dependencies import (
    get_discovery_service,
    get_search_session_store,
    get_supabase_persistence_service,
)
from app.core.categories import BusinessCategory
from app.core.config import Settings
from app.db.supabase import (
    SupabaseClient,
    SupabasePersistenceError,
    SupabasePersistenceService,
    is_persistable_lead,
)
from app.main import app
from app.models.business import Business, BusinessAddress, FieldProvenance
from app.models.discovery import DiscoveryResult
from app.models.enrichment import EnrichedField, EnrichmentFields, EnrichmentResult
from app.models.location import ResolvedLocation
from app.models.search_session import SearchSession
from app.services.business_discovery import BusinessDiscoveryService
from app.services.location_resolver import LocationResolver
from app.services.search_sessions import SearchSessionStore


class MemorySupabaseClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, Any]], str]] = []
        self.rows: dict[str, dict[str, dict[str, Any]]] = {
            "search_sessions": {},
            "leads": {},
        }

    async def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str,
    ) -> None:
        copied = [dict(row) for row in rows]
        self.calls.append((table, copied, on_conflict))
        for row in copied:
            key = str(row[on_conflict])
            self.rows[table][key] = {**self.rows[table].get(key, {}), **row}


class ContactableProvider:
    async def discover(
        self,
        *,
        location: ResolvedLocation,
        category: BusinessCategory,
        limit: int,
    ) -> list[Business]:
        return [business(phone="+49 30 123456")]


class FailingPersistenceService(SupabasePersistenceService):
    async def persist_search_session(self, session: SearchSession):
        raise SupabasePersistenceError("Supabase upsert failed with HTTP 503.")


def business(
    *,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    lead_id: str | None = "lead:stable",
) -> Business:
    return Business(
        source_id="node:123",
        source="openstreetmap",
        lead_id=lead_id,
        name="ABC Dental Clinic",
        category="Dentist",
        address=BusinessAddress(
            city="Berlin",
            state="Berlin",
            country="Germany",
            formatted="Berlin, Germany",
        ),
        latitude=52.52,
        longitude=13.405,
        phone=phone,
        email=email,
        website=website,
        opening_hours=None,
        phones=(phone,) if phone else (),
        emails=(email,) if email else (),
        websites=(website,) if website else (),
        website_type="official" if website else "none",
        website_status="listed" if website else "not_found",
        sources=("openstreetmap",),
        source_ids={"openstreetmap": ("node:123",)},
    )


def discovery(values: list[Business]) -> DiscoveryResult:
    return DiscoveryResult(
        location=ResolvedLocation(
            country_code="DE",
            country="Germany",
            region="Berlin",
            city="Berlin",
            region_query_names=("Berlin",),
            city_query_names=("Berlin",),
        ),
        businesses=values,
    )


def session_with(values: list[Business]) -> SearchSession:
    return SearchSessionStore(now_fn=lambda: datetime(2026, 9, 1, tzinfo=UTC)).create(
        result=discovery(values),
        category="Dentist",
        requested_limit=100,
        effective_limit=100,
    )


def test_supabase_configuration_supports_secret_and_legacy_names(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co/")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_primary")
    settings = Settings(_env_file=None)

    assert settings.supabase_enabled is True
    assert settings.supabase_url == "https://project.supabase.co"
    assert settings.supabase_secret_key == "sb_secret_primary"
    assert "sb_secret_primary" not in repr(settings)

    monkeypatch.delenv("SUPABASE_SECRET_KEY")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "legacy-service-role")
    legacy = Settings(_env_file=None)
    assert legacy.supabase_secret_key == "legacy-service-role"


def test_half_configured_supabase_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(ValidationError, match="must be configured together"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (business(phone="+49 30 123456"), True),
        (business(email="hello@example.com"), True),
        (business(website="https://clinic.example"), True),
        (business(website="https://facebook.com/clinic"), False),
        (business(), False),
        (business(phone="+49 30 123456", lead_id=None), False),
    ],
)
def test_lead_eligibility_gate(value: Business, expected: bool) -> None:
    assert is_persistable_lead(value) is expected


@pytest.mark.asyncio
async def test_search_session_and_only_eligible_leads_are_upserted() -> None:
    client = MemorySupabaseClient()
    service = SupabasePersistenceService(client)  # type: ignore[arg-type]
    session = session_with([business(phone="+49 30 123456"), replace(business(), lead_id="lead:2")])

    result = await service.persist_search_session(session)

    assert result.session_persisted is True
    assert result.eligible_leads == 1
    assert result.leads_persisted == 1
    stored_session = client.rows["search_sessions"][session.session_id]
    assert stored_session["result_count"] == 2
    assert stored_session["eligible_lead_count"] == 1
    assert stored_session["city"] == "Berlin"
    stored_lead = client.rows["leads"]["lead:stable"]
    assert stored_lead["search_session_id"] == session.session_id
    assert stored_lead["phone"] == "+49 30 123456"
    assert client.calls[1][2] == "lead_id"


@pytest.mark.asyncio
async def test_repeated_search_upsert_prevents_duplicate_leads() -> None:
    client = MemorySupabaseClient()
    service = SupabasePersistenceService(client)  # type: ignore[arg-type]
    session = session_with([business(phone="+49 30 123456")])

    await service.persist_search_session(session)
    first_seen = client.rows["leads"]["lead:stable"]["last_seen_at"]
    await service.persist_search_session(session)

    assert len(client.rows["leads"]) == 1
    assert client.rows["leads"]["lead:stable"]["last_seen_at"] >= first_seen
    assert [call[2] for call in client.calls if call[0] == "leads"] == [
        "lead_id",
        "lead_id",
    ]


@pytest.mark.asyncio
async def test_enrichment_makes_candidate_eligible_and_updates_persisted_row() -> None:
    client = MemorySupabaseClient()
    service = SupabasePersistenceService(client)  # type: ignore[arg-type]
    store = SearchSessionStore()
    session = store.create(
        result=discovery([business()]),
        category="Dentist",
        requested_limit=100,
        effective_limit=100,
    )
    initial = await service.persist_search_session(session)
    assert initial.leads_persisted == 0

    result = EnrichmentResult(
        source_id="node:123",
        status="partial",
        website_status="unknown",
        fields=EnrichmentFields(
            email=EnrichedField(
                primary=FieldProvenance(
                    "hello@clinic.example",
                    "official_website",
                    "high",
                )
            )
        ),
    )
    updated = store.apply_enrichment_results(session.session_id, [result])
    persisted = await service.persist_enrichment(
        updated,
        source_ids={"node:123"},
        enrichment_results=[result],
    )

    assert persisted.leads_persisted == 1
    stored = client.rows["leads"]["lead:stable"]
    assert stored["email"] == "hello@clinic.example"
    assert stored["enrichment_status"] == "partial"
    assert stored["enrichment_metadata"]["reason_code"] is None
    assert stored["enrichment_metadata"]["status"] == "partial"


@pytest.mark.asyncio
async def test_supabase_client_uses_safe_headers_and_upsert_contract() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201)

    client = SupabaseClient(
        url="https://project.supabase.co",
        secret_key="sb_secret_backend",
        transport=httpx.MockTransport(handler),
    )
    await client.upsert("leads", [{"lead_id": "lead:1"}], on_conflict="lead_id")

    request = requests[0]
    assert request.url.path == "/rest/v1/leads"
    assert request.url.params["on_conflict"] == "lead_id"
    assert request.headers["apikey"] == "sb_secret_backend"
    assert "authorization" not in request.headers
    assert "resolution=merge-duplicates" in request.headers["prefer"]


@pytest.mark.asyncio
async def test_supabase_failure_is_safe_and_does_not_leak_key() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    secret = "sb_secret_do_not_log"
    client = SupabaseClient(
        url="https://project.supabase.co",
        secret_key=secret,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(SupabasePersistenceError) as captured:
        await client.upsert("leads", [{"lead_id": "lead:1"}], on_conflict="lead_id")

    assert "HTTP 503" in str(captured.value)
    assert secret not in str(captured.value)


@pytest.mark.asyncio
async def test_discovery_survives_persistence_failure_with_warning(api_client) -> None:
    discovery_service = BusinessDiscoveryService(
        provider=ContactableProvider(),
        location_resolver=LocationResolver(),
    )
    sessions = SearchSessionStore()
    app.dependency_overrides[get_discovery_service] = lambda: discovery_service
    app.dependency_overrides[get_search_session_store] = lambda: sessions
    app.dependency_overrides[get_supabase_persistence_service] = lambda: FailingPersistenceService()
    try:
        response = await api_client.post(
            "/api/v1/businesses/discover",
            json={
                "countryCode": "DE",
                "region": None,
                "city": "Berlin",
                "category": "Dentist",
                "limit": 100,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["warnings"][-1] == (
        "Lead results were returned, but persistent storage is currently unavailable."
    )
