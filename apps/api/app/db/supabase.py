from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi.encoders import jsonable_encoder

from app.core.websites import classify_website_url
from app.models.business import Business
from app.models.enrichment import EnrichmentResult
from app.models.search_session import SearchSession

_UPSERT_BATCH_SIZE = 250


class SupabasePersistenceError(RuntimeError):
    """A safe persistence error that never contains Supabase credentials."""


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    enabled: bool
    session_persisted: bool = False
    eligible_leads: int = 0
    leads_persisted: int = 0


class SupabaseClient:
    """Small server-only PostgREST client for the two LeadRadar tables."""

    def __init__(
        self,
        *,
        url: str,
        secret_key: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not url or not secret_key:
            raise ValueError("Supabase URL and secret key are required.")
        self._base_url = url.rstrip("/")
        self._secret_key = secret_key
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {
            "apikey": self._secret_key,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
            "User-Agent": "LeadRadar-API/0.2",
        }
        # New opaque Supabase secret keys must not be presented as JWTs. Legacy
        # service-role keys are JWTs and still require the bearer header.
        if not self._secret_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self._secret_key}"
        return headers

    async def upsert(
        self,
        table: str,
        rows: Sequence[dict[str, Any]],
        *,
        on_conflict: str,
    ) -> None:
        if not rows:
            return
        if table not in {"search_sessions", "leads"}:
            raise ValueError(f"Unsupported Supabase table: {table}")
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers(),
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            try:
                response = await client.post(
                    f"/rest/v1/{table}",
                    params={"on_conflict": on_conflict},
                    json=list(rows),
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise SupabasePersistenceError(
                    f"Supabase upsert for {table} failed with HTTP {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise SupabasePersistenceError(
                    f"Supabase upsert for {table} could not reach the database."
                ) from exc


class SupabasePersistenceService:
    """Maps source-neutral LeadRadar models to Supabase and performs upserts."""

    def __init__(self, client: SupabaseClient | None = None) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def persist_search_session(
        self,
        session: SearchSession,
    ) -> PersistenceResult:
        if self._client is None:
            return PersistenceResult(enabled=False)

        eligible = [business for business in session.businesses if is_persistable_lead(business)]
        await self._client.upsert(
            "search_sessions",
            [_search_session_row(session, eligible_lead_count=len(eligible))],
            on_conflict="session_id",
        )
        stored = await self._upsert_leads(
            eligible,
            search_session_id=session.session_id,
            enrichment_metadata_by_source={},
        )
        return PersistenceResult(
            enabled=True,
            session_persisted=True,
            eligible_leads=len(eligible),
            leads_persisted=stored,
        )

    async def persist_enrichment(
        self,
        session: SearchSession,
        *,
        source_ids: set[str],
        enrichment_results: Sequence[EnrichmentResult] = (),
    ) -> PersistenceResult:
        if self._client is None:
            return PersistenceResult(enabled=False)

        all_eligible = [
            business for business in session.businesses if is_persistable_lead(business)
        ]
        changed_eligible = [
            business for business in all_eligible if business.source_id in source_ids
        ]
        await self._client.upsert(
            "search_sessions",
            [_search_session_row(session, eligible_lead_count=len(all_eligible))],
            on_conflict="session_id",
        )
        stored = await self._upsert_leads(
            changed_eligible,
            search_session_id=session.session_id,
            enrichment_metadata_by_source={
                result.source_id: _enrichment_result_metadata(result)
                for result in enrichment_results
            },
        )
        return PersistenceResult(
            enabled=True,
            session_persisted=True,
            eligible_leads=len(changed_eligible),
            leads_persisted=stored,
        )

    async def persist_businesses(
        self,
        businesses: Iterable[Business],
        *,
        enrichment_results: Sequence[EnrichmentResult] = (),
    ) -> PersistenceResult:
        if self._client is None:
            return PersistenceResult(enabled=False)
        eligible = [business for business in businesses if is_persistable_lead(business)]
        stored = await self._upsert_leads(
            eligible,
            search_session_id=None,
            enrichment_metadata_by_source={
                result.source_id: _enrichment_result_metadata(result)
                for result in enrichment_results
            },
        )
        return PersistenceResult(
            enabled=True,
            eligible_leads=len(eligible),
            leads_persisted=stored,
        )

    async def _upsert_leads(
        self,
        businesses: Sequence[Business],
        *,
        search_session_id: str | None,
        enrichment_metadata_by_source: dict[str, dict[str, Any]],
    ) -> int:
        if self._client is None:
            return 0
        rows = [
            _lead_row(
                business,
                search_session_id=search_session_id,
                enrichment_metadata=enrichment_metadata_by_source.get(business.source_id),
            )
            for business in businesses
        ]
        for offset in range(0, len(rows), _UPSERT_BATCH_SIZE):
            await self._client.upsert(
                "leads",
                rows[offset : offset + _UPSERT_BATCH_SIZE],
                on_conflict="lead_id",
            )
        return len(rows)


def is_persistable_lead(business: Business) -> bool:
    """Return whether a normalized lead has a stable ID and a public contact path."""

    websites = tuple(
        value
        for value in (business.website, *business.websites)
        if value and classify_website_url(value) == "official"
    )
    return bool(
        business.lead_id
        and (business.phone or business.phones or business.email or business.emails or websites)
    )


def _search_session_row(
    session: SearchSession,
    *,
    eligible_lead_count: int,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "session_id": session.session_id,
        "category": session.category,
        "country_code": session.location.country_code,
        "country": session.location.country,
        "region": session.location.region,
        "city": session.location.city,
        "location": jsonable_encoder(session.location),
        "requested_limit": str(session.requested_limit),
        "effective_limit": session.effective_limit,
        "providers": jsonable_encoder(session.providers),
        "warnings": list(session.warnings),
        "result_count": len(session.businesses),
        "eligible_lead_count": eligible_lead_count,
        "expires_at": session.expires_at.isoformat(),
        "created_at": session.created_at.isoformat(),
        "updated_at": now,
    }


def _lead_row(
    business: Business,
    *,
    search_session_id: str | None,
    enrichment_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if business.lead_id is None:
        raise ValueError("A stable lead_id is required for Supabase persistence.")
    now = datetime.now(UTC).isoformat()
    row = {
        "lead_id": business.lead_id,
        "source_id": business.source_id,
        "source_provider": business.source,
        "sources": list(business.sources or (business.source,)),
        "source_ids": jsonable_encoder(business.source_ids),
        "business_name": business.name,
        "category": business.category,
        "subcategories": list(business.subcategories),
        "country": business.address.country,
        "region": business.address.state,
        "city": business.address.city,
        "address": business.address.formatted,
        "address_details": jsonable_encoder(business.address),
        "latitude": business.latitude,
        "longitude": business.longitude,
        "phone": business.phone,
        "phones": list(business.phones),
        "normalized_phones": list(business.normalized_phones),
        "email": business.email,
        "emails": list(business.emails),
        "website": business.website,
        "websites": list(business.websites),
        "website_status": business.website_status,
        "website_type": business.website_type,
        "directory_links": list(business.directory_links),
        "social_links": list(business.social_links),
        "whatsapp_number": business.whatsapp_number,
        "whatsapp_numbers": list(business.whatsapp_numbers),
        "opening_hours": business.opening_hours,
        "rating": business.rating,
        "review_count": business.review_count,
        "rating_source": business.rating_source,
        "confidence": business.confidence,
        "field_provenance": jsonable_encoder(business.field_provenance),
        "enrichment_status": business.enrichment_status,
        "enrichment_metadata": {
            "website_audit": (
                jsonable_encoder(asdict(business.website_audit)) if business.website_audit else None
            ),
            **(enrichment_metadata or {}),
        },
        "source_metadata": {
            "raw_tags": business.raw_tags,
            "operating_status": business.operating_status,
            "scraped_at": business.scraped_at.isoformat(),
        },
        "lead_score": business.lead_score,
        "opportunity_level": business.opportunity_level,
        "opportunity_reasons": list(business.opportunity_reasons),
        "updated_at": now,
        "last_seen_at": now,
    }
    if search_session_id is not None:
        row["search_session_id"] = search_session_id
    return row


def _enrichment_result_metadata(result: EnrichmentResult) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "status": result.status,
            "website_status": result.website_status,
            "reason_code": result.reason_code,
            "message": result.message,
            "visited_pages": result.visited_pages,
            "contact_page_url": result.contact_page_url,
        }
    )
