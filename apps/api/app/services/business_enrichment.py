import asyncio
from typing import Literal

from app.models.business import Business
from app.models.enrichment import (
    EnrichedField,
    EnrichmentFields,
    EnrichmentReasonCode,
    EnrichmentResult,
    FieldProvenance,
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
        baseline = _baseline_fields(business)
        website_url = business.website
        candidate: SearchCandidate | None = None

        if not website_url:
            try:
                candidate = await self.search_provider.find_official_website(
                    name=business.name,
                    city=business.address.city,
                    region=business.address.state,
                    country=business.address.country,
                )
            except Exception:
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
        except Exception:
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
            )

        enriched_phone_values = tuple(
            FieldProvenance(contact.value, "official_website", contact.confidence)
            for contact in inspection.phones
        )
        enriched_email_values = tuple(
            FieldProvenance(contact.value, "official_website", contact.confidence)
            for contact in inspection.emails
        )
        official_website = FieldProvenance(
            normalize_website_url(inspection.final_url) or inspection.final_url,
            "official_website",
            "high",
        )
        website_alternatives: tuple[FieldProvenance, ...] = ()
        if candidate:
            normalized_candidate = normalize_website_url(candidate.url)
            if normalized_candidate:
                website_alternatives = (
                    FieldProvenance(normalized_candidate, "search_provider", "low"),
                )

        phone_added = _contains_additional_value(enriched_phone_values, baseline.phone)
        email_added = _contains_additional_value(enriched_email_values, baseline.email)
        website_changed = _contains_additional_value((official_website,), baseline.website)
        status = determine_enrichment_status(
            execution_succeeded=True,
            website_verified=True,
            phone_added=phone_added,
            email_added=email_added,
            phone_was_missing=baseline.phone.primary is None,
            email_was_missing=baseline.email.primary is None,
            other_fields_added=website_changed,
        )
        reason_code, message = _success_reason(
            status=status,
            contact_added=phone_added or email_added,
        )
        fields = EnrichmentFields(
            phone=_merge_field(enriched_phone_values, baseline.phone),
            email=_merge_field(enriched_email_values, baseline.email),
            website=_merge_field(
                (official_website, *website_alternatives),
                baseline.website,
            ),
        )
        return EnrichmentResult(
            source_id=business.source_id,
            status=status,
            website_status="verified",
            fields=fields,
            reason_code=reason_code,
            message=message,
            visited_pages=inspection.visited_pages,
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
    phone = normalize_phone(business.phone or "")
    email = normalize_email(business.email or "")
    website = normalize_website_url(business.website or "")
    return EnrichmentFields(
        phone=EnrichedField(
            primary=FieldProvenance(phone, "openstreetmap", "medium") if phone else None,
        ),
        email=EnrichedField(
            primary=FieldProvenance(email, "openstreetmap", "medium") if email else None,
        ),
        website=EnrichedField(
            primary=FieldProvenance(website, "openstreetmap", "medium") if website else None,
        ),
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
