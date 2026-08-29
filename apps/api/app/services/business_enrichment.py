import asyncio
import logging
from dataclasses import replace
from time import perf_counter
from typing import Literal

from app.core.websites import classify_website_url
from app.models.business import Business, FieldProvenance, WebsiteAudit
from app.models.enrichment import (
    EnrichedField,
    EnrichmentFields,
    EnrichmentReasonCode,
    EnrichmentResult,
    SearchCandidate,
    WebsiteVerificationStatus,
)
from app.normalizers.contact import normalize_email, normalize_phone, normalize_website_url
from app.providers.enrichment.base import (
    BusinessSearchProvider,
    OfficialWebsiteEnrichmentProvider,
    RobotsDisallowedError,
    WebsiteAccessDeniedError,
    WebsiteDnsError,
    WebsiteParserError,
    WebsiteSafetyError,
    WebsiteTimeoutError,
    WebsiteUnavailableError,
)
from app.services.lead_scoring import score_lead

logger = logging.getLogger(__name__)

TerminalEnrichmentStatus = Literal["completed", "partial", "no_data", "failed"]


class EnrichmentBatchLimitError(ValueError):
    """The requested enrichment batch is larger than the configured safe limit."""


def determine_enrichment_status(
    *,
    execution_succeeded: bool,
    website_verified: bool,
    phone_added: bool,
    email_added: bool,
    phone_was_missing: bool,
    email_was_missing: bool,
    other_fields_added: bool = False,
) -> TerminalEnrichmentStatus:
    """Classify execution separately from the business's pre-existing contact coverage."""
    if not execution_succeeded:
        return "failed"

    useful_change = phone_added or email_added or other_fields_added
    if not useful_change and not website_verified:
        return "no_data"

    missing_contacts = int(phone_was_missing) + int(email_was_missing)
    filled_missing_contacts = int(phone_was_missing and phone_added) + int(
        email_was_missing and email_added
    )
    if missing_contacts and filled_missing_contacts == missing_contacts:
        return "completed"
    return "partial"


class BusinessEnrichmentService:
    def __init__(
        self,
        *,
        website_provider: OfficialWebsiteEnrichmentProvider,
        search_provider: BusinessSearchProvider,
        batch_limit: int = 20,
        max_concurrency: int = 4,
    ) -> None:
        self.website_provider = website_provider
        self.search_provider = search_provider
        self.batch_limit = batch_limit
        self.max_concurrency = max_concurrency

    async def enrich(self, business: Business) -> EnrichmentResult:
        started = perf_counter()
        logger.info(
            "enrichment.start",
            extra={"source_id": business.source_id, "has_website": bool(business.website)},
        )
        result = await self._enrich(business)
        phone_values = _field_values(result.fields.phone)
        email_values = _field_values(result.fields.email)
        website_values = _field_values(result.fields.website)
        whatsapp_values = _field_values(result.fields.whatsapp)
        website_status = {
            "verified": "verified",
            "unreachable": "unreachable",
            "mismatch": "mismatch",
            "source_listed": "listed",
        }.get(
            result.website_status,
            "listed" if website_values else "not_found",
        )
        scored_business = replace(
            business,
            phone=phone_values[0] if phone_values else business.phone,
            phones=phone_values or business.phones,
            normalized_phones=tuple(
                value
                for phone in (phone_values or business.phones)
                if (value := normalize_phone(phone))
            ),
            email=email_values[0] if email_values else business.email,
            emails=email_values or business.emails,
            website=website_values[0] if website_values else business.website,
            websites=website_values or business.websites,
            website_status=website_status,
            website_type=(
                "official" if result.website_status == "verified" else business.website_type
            ),
            directory_links=tuple(
                dict.fromkeys((*business.directory_links, *result.directory_links))
            ),
            social_links=tuple(dict.fromkeys((*business.social_links, *result.social_links))),
            whatsapp_number=(
                whatsapp_values[0] if whatsapp_values else business.whatsapp_number
            ),
            whatsapp_numbers=whatsapp_values or business.whatsapp_numbers,
            website_audit=result.website_audit,
            enrichment_status=result.status,
        )
        opportunity = score_lead(scored_business)
        enriched_result = replace(
            result,
            lead_score=opportunity.score,
            opportunity_level=opportunity.level,
            opportunity_reasons=opportunity.reasons,
        )
        logger.info(
            "enrichment.finish",
            extra={
                "source_id": business.source_id,
                "status": result.status,
                "reason_code": result.reason_code,
                "duration_ms": round((perf_counter() - started) * 1000),
            },
        )
        return enriched_result

    async def _enrich(self, business: Business) -> EnrichmentResult:
        baseline = _baseline_fields(business)
        listed_website_type = classify_website_url(business.website)
        website_url = (
            business.website
            if listed_website_type not in {"directory", "social"}
            else None
        )
        directory_links = tuple(
            dict.fromkeys(
                (
                    *business.directory_links,
                    *((business.website,) if listed_website_type == "directory" else ()),
                )
            )
        )
        social_links = tuple(
            dict.fromkeys(
                (
                    *business.social_links,
                    *((business.website,) if listed_website_type == "social" else ()),
                )
            )
        )
        candidate: SearchCandidate | None = None

        if not website_url:
            try:
                candidate = await self.search_provider.find_official_website(
                    name=business.name,
                    city=business.address.city,
                    region=business.address.state,
                    country=business.address.country,
                    locality=business.address.locality,
                    category=business.category,
                    phone=business.phone,
                )
            except Exception:  # noqa: BLE001 - provider boundary returns a safe domain result
                return _failed_result(
                    business=business,
                    fields=baseline,
                    website_status="unknown",
                    reason_code="PROVIDER_ERROR",
                    message="The enrichment provider could not complete the request.",
                )
            website_url = candidate.url if candidate else None

        if not website_url:
            reason_code: EnrichmentReasonCode = (
                "NO_WEBSITE_AVAILABLE"
                if self.search_provider.enabled
                else "SEARCH_PROVIDER_DISABLED"
            )
            message = (
                "No official website was found by the configured search provider."
                if self.search_provider.enabled
                else "No official website is available from the current sources."
            )
            return EnrichmentResult(
                source_id=business.source_id,
                status=determine_enrichment_status(
                    execution_succeeded=True,
                    website_verified=False,
                    phone_added=False,
                    email_added=False,
                    phone_was_missing=baseline.phone.primary is None,
                    email_was_missing=baseline.email.primary is None,
                ),
                website_status="unknown",
                fields=baseline,
                reason_code=reason_code,
                message=message,
                directory_links=directory_links,
                social_links=social_links,
            )

        try:
            inspection = await self.website_provider.inspect(
                business=business,
                website_url=website_url,
            )
        except WebsiteTimeoutError:
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="unreachable",
                reason_code="WEBSITE_TIMEOUT",
                message="The business website did not respond in time.",
            )
        except (RobotsDisallowedError, WebsiteAccessDeniedError):
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="unreachable",
                reason_code="WEBSITE_ACCESS_DENIED",
                message="The website refused automated access.",
            )
        except WebsiteDnsError:
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="unreachable",
                reason_code="DNS_ERROR",
                message="The business website address could not be resolved.",
            )
        except WebsiteParserError:
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="unknown",
                reason_code="PARSER_ERROR",
                message="The website response could not be processed.",
            )
        except WebsiteSafetyError:
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="mismatch",
                reason_code="INVALID_URL",
                message="The listed website could not be inspected safely.",
            )
        except WebsiteUnavailableError:
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="unreachable",
                reason_code="WEBSITE_UNREACHABLE",
                message="The business website could not be reached.",
            )
        except Exception:  # noqa: BLE001 - provider boundary prevents leaking internals
            return _failed_result(
                business=business,
                fields=baseline,
                website_status="unknown",
                reason_code="PROVIDER_ERROR",
                message="The enrichment provider could not complete the request.",
            )

        if inspection.verification_status != "verified" or not inspection.final_url:
            reason_code: EnrichmentReasonCode = (
                "WEBSITE_MISMATCH"
                if inspection.verification_status == "mismatch"
                else "NO_CONTACT_DETAILS_FOUND"
            )
            message = (
                "The candidate website could not be confidently matched to this business."
                if inspection.verification_status == "mismatch"
                else "The website was checked, but no additional public contact information was found."
            )
            return EnrichmentResult(
                source_id=business.source_id,
                status=determine_enrichment_status(
                    execution_succeeded=True,
                    website_verified=False,
                    phone_added=False,
                    email_added=False,
                    phone_was_missing=baseline.phone.primary is None,
                    email_was_missing=baseline.email.primary is None,
                ),
                website_status=inspection.verification_status,
                fields=baseline,
                reason_code=reason_code,
                message=message,
                visited_pages=inspection.visited_pages,
                directory_links=tuple(
                    dict.fromkeys((*directory_links, *inspection.directory_links))
                ),
                social_links=tuple(
                    dict.fromkeys((*social_links, *inspection.social_links))
                ),
                whatsapp_numbers=tuple(
                    contact.value for contact in inspection.whatsapp_numbers
                ),
                website_audit=inspection.website_audit,
            )

        enriched_phone_values = tuple(
            FieldProvenance(
                contact.value,
                "official_website",
                contact.confidence,
                source_url=contact.page_url,
                source_type=contact.source_type,
            )
            for contact in inspection.phones
        )
        enriched_email_values = tuple(
            FieldProvenance(
                contact.value,
                "official_website",
                contact.confidence,
                source_url=contact.page_url,
                source_type=contact.source_type,
            )
            for contact in inspection.emails
        )
        enriched_whatsapp_values = tuple(
            FieldProvenance(
                contact.value,
                "official_website",
                contact.confidence,
                source_url=contact.page_url,
                source_type=contact.source_type,
            )
            for contact in inspection.whatsapp_numbers
        )
        official_website = FieldProvenance(
            normalize_website_url(inspection.final_url) or inspection.final_url,
            "official_website",
            "high",
            source_url=inspection.final_url,
            source_type="verified_official",
        )
        website_alternatives: tuple[FieldProvenance, ...] = ()
        if candidate:
            normalized_candidate = normalize_website_url(candidate.url)
            if normalized_candidate:
                website_alternatives = (
                    FieldProvenance(
                        normalized_candidate,
                        "search_provider",
                        "low",
                        source_url=normalized_candidate,
                        source_type="search_candidate",
                    ),
                )

        phone_added = _contains_additional_value(enriched_phone_values, baseline.phone)
        email_added = _contains_additional_value(enriched_email_values, baseline.email)
        website_changed = _contains_additional_value((official_website,), baseline.website)
        whatsapp_added = _contains_additional_value(
            enriched_whatsapp_values,
            baseline.whatsapp,
        )
        status = determine_enrichment_status(
            execution_succeeded=True,
            website_verified=True,
            phone_added=phone_added,
            email_added=email_added,
            phone_was_missing=baseline.phone.primary is None,
            email_was_missing=baseline.email.primary is None,
            other_fields_added=website_changed or whatsapp_added,
        )
        reason_code, message = _success_reason(
            status=status,
            contact_added=phone_added or email_added or whatsapp_added,
        )
        fields = EnrichmentFields(
            phone=_merge_field(enriched_phone_values, baseline.phone),
            email=_merge_field(enriched_email_values, baseline.email),
            website=_merge_field(
                (official_website, *website_alternatives),
                baseline.website,
            ),
            whatsapp=_merge_field(enriched_whatsapp_values, baseline.whatsapp),
        )
        return EnrichmentResult(
            source_id=business.source_id,
            status=status,
            website_status="verified",
            fields=fields,
            reason_code=reason_code,
            message=message,
            visited_pages=inspection.visited_pages,
            social_links=tuple(dict.fromkeys((*social_links, *inspection.social_links))),
            directory_links=tuple(
                dict.fromkeys((*directory_links, *inspection.directory_links))
            ),
            whatsapp_numbers=tuple(
                dict.fromkeys(contact.value for contact in inspection.whatsapp_numbers)
            ),
            contact_page_url=inspection.contact_page_url,
            website_audit=inspection.website_audit,
        )

    async def enrich_batch(self, businesses: list[Business]) -> list[EnrichmentResult]:
        if len(businesses) > self.batch_limit:
            raise EnrichmentBatchLimitError(
                f"A maximum of {self.batch_limit} businesses can be enriched at once."
            )
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def enrich_one(business: Business) -> EnrichmentResult:
            async with semaphore:
                return await self.enrich(business)

        return list(await asyncio.gather(*(enrich_one(business) for business in businesses)))


def _failed_result(
    *,
    business: Business,
    fields: EnrichmentFields,
    website_status: WebsiteVerificationStatus,
    reason_code: EnrichmentReasonCode,
    message: str,
) -> EnrichmentResult:
    audit = (
        WebsiteAudit(reachable=False, label="Website unreachable")
        if website_status == "unreachable"
        else None
    )
    return EnrichmentResult(
        source_id=business.source_id,
        status=determine_enrichment_status(
            execution_succeeded=False,
            website_verified=False,
            phone_added=False,
            email_added=False,
            phone_was_missing=fields.phone.primary is None,
            email_was_missing=fields.email.primary is None,
        ),
        website_status=website_status,
        fields=fields,
        reason_code=reason_code,
        message=message,
        website_audit=audit,
    )


def _success_reason(
    *,
    status: TerminalEnrichmentStatus,
    contact_added: bool,
) -> tuple[EnrichmentReasonCode, str]:
    if status == "completed":
        return "ADDITIONAL_CONTACTS_FOUND", "Additional contact information found."
    if contact_added:
        return "PARTIAL_CONTACTS_FOUND", "Some additional public contact information was found."
    return (
        "WEBSITE_VERIFIED",
        "Official website verified; no additional public contact details were found.",
    )


def _baseline_fields(business: Business) -> EnrichmentFields:
    phone = _provenance_field(
        business,
        "phone",
        normalizer=normalize_phone,
        fallback=business.phone,
    )
    email = _provenance_field(
        business,
        "email",
        normalizer=normalize_email,
        fallback=business.email,
    )
    website = _provenance_field(
        business,
        "website",
        normalizer=_normalize_official_website,
        fallback=(
            business.website
            if classify_website_url(business.website) not in {"directory", "social"}
            else None
        ),
    )
    whatsapp = _provenance_field(
        business,
        "whatsapp",
        normalizer=normalize_phone,
        fallback=business.whatsapp_number,
    )
    return EnrichmentFields(
        phone=phone,
        email=email,
        website=website,
        whatsapp=whatsapp,
    )


def _normalize_official_website(value: str) -> str | None:
    if classify_website_url(value) in {"directory", "social"}:
        return None
    return normalize_website_url(value)


def _provenance_field(
    business: Business,
    field_name: str,
    *,
    normalizer,
    fallback: str | None,
) -> EnrichedField:
    values: list[FieldProvenance] = []
    seen: set[tuple[str, str]] = set()
    candidates = business.field_provenance.get(field_name, ())
    if not candidates and fallback:
        candidates = (FieldProvenance(fallback, business.source, "medium"),)
    for item in candidates:
        normalized = normalizer(item.value)
        if not normalized:
            continue
        key = (normalized.casefold(), item.source)
        if key in seen:
            continue
        seen.add(key)
        values.append(replace(item, value=normalized))
    return EnrichedField(
        primary=values[0] if values else None,
        alternatives=tuple(values[1:]),
    )


def _field_values(field: EnrichedField) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            item.value for item in (field.primary, *field.alternatives) if item is not None
        )
    )


def _contains_additional_value(
    candidates: tuple[FieldProvenance, ...],
    baseline: EnrichedField,
) -> bool:
    existing = {
        value.value.casefold()
        for value in (baseline.primary, *baseline.alternatives)
        if value is not None
    }
    return any(candidate.value.casefold() not in existing for candidate in candidates)


def _merge_field(
    preferred: tuple[FieldProvenance, ...],
    baseline: EnrichedField,
) -> EnrichedField:
    ordered = [*preferred]
    if baseline.primary:
        ordered.append(baseline.primary)
    ordered.extend(baseline.alternatives)
    if not ordered:
        return EnrichedField()

    seen: set[tuple[str, str]] = set()
    deduplicated: list[FieldProvenance] = []
    for value in ordered:
        key = (value.value.casefold(), value.source)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(value)
    return EnrichedField(
        primary=deduplicated[0],
        alternatives=tuple(deduplicated[1:]),
    )
