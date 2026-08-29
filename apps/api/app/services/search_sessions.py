import math
import secrets
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.core.websites import classify_website_url
from app.models.business import Business
from app.models.discovery import DiscoveryResult
from app.models.enrichment import EnrichedField, EnrichmentResult
from app.models.search_session import SearchFilter, SearchSession, SearchSessionPage
from app.normalizers.contact import normalize_phone


class SearchSessionNotFoundError(LookupError):
    """The requested session is unknown, expired, or was evicted for safety."""


class SearchSessionCapacityError(ValueError):
    """A result set is larger than the configured in-memory safety bound."""


class SearchSessionStore:
    """Bounded process-local result storage; sessions never outlive this API process."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 1_800,
        max_sessions: int = 20,
        max_records: int = 10_000,
        time_fn: Callable[[], float] = time.monotonic,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self.max_records = max_records
        self._time_fn = time_fn
        self._now_fn = now_fn
        self._sessions: OrderedDict[str, SearchSession] = OrderedDict()
        self._lock = threading.RLock()

    def create(
        self,
        *,
        result: DiscoveryResult,
        category: str,
        requested_limit: int | str,
        effective_limit: int,
    ) -> SearchSession:
        if len(result.businesses) > self.max_records:
            raise SearchSessionCapacityError(
                "The result set exceeds the configured in-memory session capacity."
            )
        now_monotonic = self._time_fn()
        created_at = self._now_fn()
        session = SearchSession(
            session_id=secrets.token_urlsafe(18),
            location=result.location,
            category=category,
            requested_limit="all" if requested_limit == "all" else int(requested_limit),
            effective_limit=effective_limit,
            businesses=list(result.businesses),
            providers=result.providers,
            warnings=result.warnings,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=self.ttl_seconds),
            expires_monotonic=now_monotonic + self.ttl_seconds,
        )
        with self._lock:
            self._purge_expired(now_monotonic)
            self._sessions[session.session_id] = session
            while (
                len(self._sessions) > self.max_sessions
                or self._record_count() > self.max_records
            ):
                self._sessions.popitem(last=False)
        return session

    def get(self, session_id: str) -> SearchSession:
        with self._lock:
            now = self._time_fn()
            self._purge_expired(now)
            session = self._sessions.get(session_id)
            if session is None:
                raise SearchSessionNotFoundError(
                    "This search session is unavailable or expired. Run the search again."
                )
            return session

    def page(
        self,
        session_id: str,
        *,
        page: int,
        page_size: int,
        filter_name: SearchFilter,
    ) -> SearchSessionPage:
        session = self.get(session_id)
        filtered = filter_businesses(session.businesses, filter_name)
        total_count = len(filtered)
        total_pages = math.ceil(total_count / page_size) if total_count else 0
        offset = (page - 1) * page_size
        return SearchSessionPage(
            session=session,
            businesses=tuple(filtered[offset : offset + page_size]),
            filter_name=filter_name,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            summary=summarize_businesses(filtered),
            enrichment_progress=enrichment_progress(session.businesses),
        )

    def filtered(
        self,
        session_id: str,
        filter_name: SearchFilter,
    ) -> tuple[SearchSession, list[Business]]:
        session = self.get(session_id)
        return session, filter_businesses(session.businesses, filter_name)

    def enrichment_candidates(
        self,
        session_id: str,
        *,
        lead_ids: set[str] | None,
        batch_size: int,
        retry_failed: bool,
    ) -> tuple[SearchSession, list[Business]]:
        session = self.get(session_id)
        eligible = [
            business
            for business in session.businesses
            if (not lead_ids or business.lead_id in lead_ids)
            and business.enrichment_status not in {"completed", "partial", "no_data"}
            and (retry_failed or business.enrichment_status != "failed")
        ]
        eligible.sort(key=_enrichment_priority)
        return session, eligible[:batch_size]

    def apply_enrichment_results(
        self,
        session_id: str,
        results: list[EnrichmentResult],
    ) -> SearchSession:
        with self._lock:
            session = self.get(session_id)
            result_by_source = {result.source_id: result for result in results}
            session.businesses = [
                apply_enrichment_result(business, result_by_source[business.source_id])
                if business.source_id in result_by_source
                else business
                for business in session.businesses
            ]
            return session

    def _purge_expired(self, now: float) -> None:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_monotonic <= now
        ]
        for session_id in expired:
            del self._sessions[session_id]

    def _record_count(self) -> int:
        return sum(len(session.businesses) for session in self._sessions.values())


def filter_businesses(
    businesses: list[Business],
    filter_name: SearchFilter,
) -> list[Business]:
    if filter_name == "all":
        return list(businesses)
    predicates = {
        "phone": lambda value: bool(value.phone or value.phones),
        "email": lambda value: bool(value.email or value.emails),
        "official_website": _has_official_website,
        "no_official_website": lambda value: not _has_official_website(value),
        "directory_social_only": lambda value: (
            not _has_official_website(value)
            and bool(value.directory_links or value.social_links)
        ),
        "opportunity_high": lambda value: value.opportunity_level == "High",
        "opportunity_medium": lambda value: value.opportunity_level == "Medium",
        "opportunity_low": lambda value: value.opportunity_level == "Low",
        "enrichment_pending": lambda value: value.enrichment_status
        in {"not_started", "in_progress"},
        "enrichment_complete": lambda value: value.enrichment_status
        in {"completed", "partial", "no_data"},
    }
    return [business for business in businesses if predicates[filter_name](business)]


def summarize_businesses(businesses: list[Business]) -> dict[str, int]:
    return {
        "total": len(businesses),
        "withPhone": sum(bool(value.phone or value.phones) for value in businesses),
        "withEmail": sum(bool(value.email or value.emails) for value in businesses),
        "withOfficialWebsite": sum(_has_official_website(value) for value in businesses),
        "withoutOfficialWebsite": sum(
            not _has_official_website(value) for value in businesses
        ),
        "directoryOrSocialOnly": sum(
            not _has_official_website(value)
            and bool(value.directory_links or value.social_links)
            for value in businesses
        ),
        "highOpportunity": sum(value.opportunity_level == "High" for value in businesses),
        "mediumOpportunity": sum(
            value.opportunity_level == "Medium" for value in businesses
        ),
        "lowOpportunity": sum(value.opportunity_level == "Low" for value in businesses),
    }


def enrichment_progress(businesses: list[Business]) -> dict[str, int]:
    processed = sum(
        value.enrichment_status in {"completed", "partial", "no_data", "failed"}
        for value in businesses
    )
    return {
        "total": len(businesses),
        "processed": processed,
        "pending": len(businesses) - processed,
        "failed": sum(value.enrichment_status == "failed" for value in businesses),
    }


def apply_enrichment_result(business: Business, result: EnrichmentResult) -> Business:
    phones = _field_values(result.fields.phone)
    emails = _field_values(result.fields.email)
    websites = _field_values(result.fields.website)
    whatsapp_numbers = _field_values(result.fields.whatsapp)
    provenance = dict(business.field_provenance)
    for name, field in (
        ("phone", result.fields.phone),
        ("email", result.fields.email),
        ("website", result.fields.website),
        ("whatsapp", result.fields.whatsapp),
    ):
        values = tuple(value for value in (field.primary, *field.alternatives) if value)
        if values:
            provenance[name] = values
    website_status = {
        "verified": "verified",
        "unreachable": "unreachable",
        "mismatch": "mismatch",
        "source_listed": "listed",
    }.get(result.website_status, business.website_status)
    return replace(
        business,
        phone=phones[0] if phones else business.phone,
        phones=phones or business.phones,
        normalized_phones=tuple(
            normalized
            for value in (phones or business.phones)
            if (normalized := normalize_phone(value))
        ),
        email=emails[0] if emails else business.email,
        emails=emails or business.emails,
        website=websites[0] if websites else business.website,
        websites=websites or business.websites,
        website_status=website_status,
        website_type="official" if result.website_status == "verified" else business.website_type,
        directory_links=tuple(
            dict.fromkeys((*business.directory_links, *result.directory_links))
        ),
        social_links=tuple(dict.fromkeys((*business.social_links, *result.social_links))),
        whatsapp_number=(
            whatsapp_numbers[0] if whatsapp_numbers else business.whatsapp_number
        ),
        whatsapp_numbers=whatsapp_numbers or business.whatsapp_numbers,
        field_provenance=provenance,
        enrichment_status=result.status,
        website_audit=result.website_audit or business.website_audit,
        lead_score=result.lead_score,
        opportunity_level=result.opportunity_level,
        opportunity_reasons=result.opportunity_reasons,
    )


def _field_values(field: EnrichedField) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            value.value
            for value in (field.primary, *field.alternatives)
            if value is not None
        )
    )


def _has_official_website(business: Business) -> bool:
    return bool(
        business.website
        and business.website_type == "official"
        and classify_website_url(business.website) == "official"
    )


def _enrichment_priority(business: Business) -> tuple[int, int, str]:
    has_phone = bool(business.phone or business.phones)
    has_official = _has_official_website(business)
    has_email = bool(business.email or business.emails)
    priority = (
        0
        if has_phone and not has_official
        else 1
        if has_phone and has_official and not has_email
        else 2
    )
    return priority, -business.lead_score, business.name.casefold()
