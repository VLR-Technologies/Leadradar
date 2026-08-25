import pytest

from app.models.business import Business, BusinessAddress
from app.models.enrichment import ExtractedContact, WebsiteInspection
from app.providers.enrichment.base import (
    WebsiteDnsError,
    WebsiteParserError,
    WebsiteTimeoutError,
)
from app.providers.enrichment.search import DisabledBusinessSearchProvider
from app.services.business_enrichment import (
    BusinessEnrichmentService,
    EnrichmentBatchLimitError,
    determine_enrichment_status,
)


def business(
    *,
    source_id: str = "node:123",
    phone: str | None = None,
    email: str | None = None,
    website: str | None = "https://abcdental.in",
) -> Business:
    return Business(
        source_id=source_id,
        source="openstreetmap",
        name="ABC Dental Clinic",
        category="Dentist",
        address=BusinessAddress(city="Hyderabad", state="Telangana", country="India"),
        latitude=17.4,
        longitude=78.4,
        phone=phone,
        email=email,
        website=website,
        opening_hours=None,
    )


class StaticWebsiteProvider:
    def __init__(self, inspection: WebsiteInspection) -> None:
        self.inspection = inspection

    async def inspect(self, *, business: Business, website_url: str) -> WebsiteInspection:
        return self.inspection


class RaisingWebsiteProvider:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def inspect(self, *, business: Business, website_url: str) -> WebsiteInspection:
        raise self.error


class FailingSearchProvider:
    enabled = True

    async def find_official_website(self, **kwargs):
        raise RuntimeError("secret provider detail")


def verified_inspection(
    *,
    phones: tuple[str, ...] = (),
    emails: tuple[str, ...] = (),
) -> WebsiteInspection:
    website_url = "https://abcdental.in"
    return WebsiteInspection(
        verification_status="verified",
        final_url=website_url,
        phones=tuple(ExtractedContact(value, "high", website_url) for value in phones),
        emails=tuple(ExtractedContact(value, "high", website_url) for value in emails),
        visited_pages=(website_url, f"{website_url}/contact"),
        message="Provider detail is replaced by service messaging.",
    )


def service(
    website_provider=None,
    *,
    search_provider=None,
    batch_limit: int = 20,
) -> BusinessEnrichmentService:
    return BusinessEnrichmentService(
        website_provider=website_provider or StaticWebsiteProvider(verified_inspection()),
        search_provider=search_provider or DisabledBusinessSearchProvider(),
        batch_limit=batch_limit,
        max_concurrency=2,
    )


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"execution_succeeded": False}, "failed"),
        ({"execution_succeeded": True}, "no_data"),
        ({"execution_succeeded": True, "website_verified": True}, "partial"),
        ({"execution_succeeded": True, "phone_added": True}, "partial"),
        (
            {
                "execution_succeeded": True,
                "phone_added": True,
                "email_added": True,
            },
            "completed",
        ),
    ],
)
def test_central_status_decision_table(arguments: dict, expected: str) -> None:
    values = {
        "execution_succeeded": False,
        "website_verified": False,
        "phone_added": False,
        "email_added": False,
        "phone_was_missing": True,
        "email_was_missing": True,
    }
    values.update(arguments)
    assert determine_enrichment_status(**values) == expected


@pytest.mark.asyncio
async def test_completed_when_all_missing_contacts_are_added() -> None:
    result = await service(
        StaticWebsiteProvider(
            verified_inspection(
                phones=("+919876543210",),
                emails=("info@abcdental.in",),
            )
        )
    ).enrich(business())

    assert result.status == "completed"
    assert result.reason_code == "ADDITIONAL_CONTACTS_FOUND"
    assert result.message == "Additional contact information found."


@pytest.mark.asyncio
async def test_verified_website_wins_and_osm_conflict_is_preserved() -> None:
    result = await service(
        StaticWebsiteProvider(
            verified_inspection(
                phones=("+919876543210",),
                emails=("info@abcdental.in",),
            )
        )
    ).enrich(business(phone="040-12345678"))

    assert result.status == "completed"
    assert result.website_status == "verified"
    assert result.fields.phone.primary is not None
    assert result.fields.phone.primary.value == "+919876543210"
    assert result.fields.phone.primary.source == "official_website"
    assert [(item.value, item.source) for item in result.fields.phone.alternatives] == [
        ("040-12345678", "openstreetmap")
    ]


@pytest.mark.asyncio
async def test_phone_only_improvement_is_partial() -> None:
    result = await service(
        StaticWebsiteProvider(verified_inspection(phones=("+919876543210",)))
    ).enrich(business())

    assert result.status == "partial"
    assert result.reason_code == "PARTIAL_CONTACTS_FOUND"
    assert result.fields.phone.primary is not None
    assert result.fields.email.primary is None


@pytest.mark.asyncio
async def test_verified_website_without_new_contacts_is_partial() -> None:
    result = await service().enrich(business())

    assert result.status == "partial"
    assert result.website_status == "verified"
    assert result.reason_code == "WEBSITE_VERIFIED"
    assert result.message == (
        "Official website verified; no additional public contact details were found."
    )


@pytest.mark.asyncio
async def test_successful_unverified_crawl_without_contacts_is_no_data() -> None:
    inspection = WebsiteInspection(
        verification_status="unknown",
        final_url="https://abcdental.in",
        visited_pages=("https://abcdental.in",),
    )
    result = await service(StaticWebsiteProvider(inspection)).enrich(business())

    assert result.status == "no_data"
    assert result.reason_code == "NO_CONTACT_DETAILS_FOUND"


@pytest.mark.asyncio
async def test_missing_website_and_disabled_search_is_no_data() -> None:
    result = await service().enrich(business(website=None))

    assert result.status == "no_data"
    assert result.website_status == "unknown"
    assert result.reason_code == "SEARCH_PROVIDER_DISABLED"
    assert result.message == "No official website is available from the current sources."


@pytest.mark.asyncio
async def test_no_data_outcome_keeps_existing_osm_phone() -> None:
    result = await service().enrich(
        business(phone="040-12345678", website=None)
    )

    assert result.status == "no_data"
    assert result.fields.phone.primary is not None
    assert result.fields.phone.primary.value == "040-12345678"
    assert result.fields.phone.primary.source == "openstreetmap"


@pytest.mark.asyncio
async def test_existing_osm_phone_is_preserved_when_no_new_contact_is_found() -> None:
    result = await service().enrich(business(phone="040-12345678"))

    assert result.status == "partial"
    assert result.fields.phone.primary is not None
    assert result.fields.phone.primary.value == "040-12345678"
    assert any(
        item.source == "openstreetmap"
        for item in (result.fields.phone.primary, *result.fields.phone.alternatives)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "reason_code", "message"),
    [
        (
            WebsiteTimeoutError(),
            "WEBSITE_TIMEOUT",
            "The business website did not respond in time.",
        ),
        (
            WebsiteDnsError(),
            "DNS_ERROR",
            "The business website address could not be resolved.",
        ),
        (
            WebsiteParserError(),
            "PARSER_ERROR",
            "The website response could not be processed.",
        ),
        (
            RuntimeError("secret provider detail"),
            "PROVIDER_ERROR",
            "The enrichment provider could not complete the request.",
        ),
    ],
)
async def test_technical_provider_errors_are_failed_with_safe_messages(
    error: Exception,
    reason_code: str,
    message: str,
) -> None:
    result = await service(RaisingWebsiteProvider(error)).enrich(
        business(phone="040-12345678")
    )

    assert result.status == "failed"
    assert result.reason_code == reason_code
    assert result.message == message
    assert result.fields.phone.primary is not None


@pytest.mark.asyncio
async def test_search_provider_error_is_failed_without_exposing_exception() -> None:
    result = await service(search_provider=FailingSearchProvider()).enrich(
        business(website=None)
    )

    assert result.status == "failed"
    assert result.reason_code == "PROVIDER_ERROR"
    assert result.message == "The enrichment provider could not complete the request."


@pytest.mark.asyncio
async def test_batch_limit_is_enforced() -> None:
    with pytest.raises(EnrichmentBatchLimitError):
        await service(batch_limit=2).enrich_batch(
            [business(source_id=f"node:{index}") for index in range(3)]
        )
