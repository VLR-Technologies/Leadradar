import httpx
import pytest

from app.models.business import Business, BusinessAddress
from app.providers.enrichment.base import (
    WebsiteAccessDeniedError,
    WebsiteSafetyError,
    WebsiteUnavailableError,
)
from app.providers.enrichment.website import WebsiteEnrichmentProvider


async def allow_host(_: str) -> None:
    return None


def business(*, website: str | None = "https://abcdental.in") -> Business:
    return Business(
        source_id="node:123",
        source="openstreetmap",
        name="ABC Dental Clinic",
        category="Dentist",
        address=BusinessAddress(city="Hyderabad", state="Telangana", country="India"),
        latitude=17.4,
        longitude=78.4,
        phone=None,
        email=None,
        website=website,
        opening_hours=None,
    )


def provider(handler) -> WebsiteEnrichmentProvider:
    return WebsiteEnrichmentProvider(
        transport=httpx.MockTransport(handler),
        host_validator=allow_host,
        max_pages=4,
    )


@pytest.mark.asyncio
async def test_verifies_official_website_and_inspects_contact_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if request.url.path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    "<title>ABC Dental Clinic Hyderabad</title>"
                    '<a href="/contact-us">Reach Us</a>'
                ),
            )
        if request.url.path == "/contact-us":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    "<h1>ABC Dental Clinic Hyderabad</h1>"
                    '<a href="tel:+91 9876543210">Call</a>'
                    '<a href="mailto:info@abcdental.in">Email</a>'
                ),
            )
        return httpx.Response(404)

    result = await provider(handler).inspect(
        business=business(),
        website_url="https://abcdental.in",
    )

    assert result.verification_status == "verified"
    assert [phone.value for phone in result.phones] == ["+919876543210"]
    assert [email.value for email in result.emails] == ["info@abcdental.in"]
    assert result.visited_pages == (
        "https://abcdental.in",
        "https://abcdental.in/contact-us",
    )
    assert result.contact_page_url == "https://abcdental.in/contact-us"
    assert result.website_audit is not None
    assert result.website_audit.reachable is True
    assert result.website_audit.uses_https is True
    assert result.website_audit.contact_page_present is True
    assert result.website_audit.email_present is True
    assert result.website_audit.phone_present is True
    assert result.website_audit.label == "Potential improvement opportunity"


@pytest.mark.asyncio
async def test_accepts_same_domain_redirect_and_uses_final_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/":
            return httpx.Response(301, headers={"location": "/home"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<title>ABC Dental Clinic Hyderabad</title>",
        )

    result = await provider(handler).inspect(
        business=business(),
        website_url="https://abcdental.in",
    )

    assert result.verification_status == "verified"
    assert result.final_url == "https://abcdental.in/home"


@pytest.mark.asyncio
async def test_marks_unrelated_candidate_as_mismatch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<title>Unrelated Hardware Store in Pune</title>",
        )

    result = await provider(handler).inspect(
        business=business(),
        website_url="https://abcdental.in",
    )

    assert result.verification_status == "mismatch"
    assert result.phones == ()


@pytest.mark.asyncio
async def test_unreachable_website_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(WebsiteUnavailableError):
        await provider(handler).inspect(
            business=business(),
            website_url="https://abcdental.in",
        )


@pytest.mark.asyncio
async def test_robots_disallow_prevents_homepage_fetch() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /")

    from app.providers.enrichment.base import RobotsDisallowedError

    with pytest.raises(RobotsDisallowedError):
        await provider(handler).inspect(
            business=business(),
            website_url="https://abcdental.in",
        )
    assert requested_paths == ["/robots.txt"]


@pytest.mark.asyncio
async def test_third_party_directory_page_is_not_crawled() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Blocked platform URL should not be requested")

    with pytest.raises(WebsiteSafetyError):
        await provider(handler).inspect(
            business=business(website="https://www.zomato.com/hyderabad/abc"),
            website_url="https://www.zomato.com/hyderabad/abc",
        )


@pytest.mark.asyncio
async def test_explicit_http_forbidden_response_is_access_denied() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(403)

    with pytest.raises(WebsiteAccessDeniedError):
        await provider(handler).inspect(
            business=business(),
            website_url="https://abcdental.in",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://127.0.0.1",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1",
        "file:///etc/passwd",
    ],
)
async def test_private_and_unsupported_urls_are_rejected_before_fetch(
    unsafe_url: str,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("Unsafe URL should not be requested")

    with pytest.raises(WebsiteSafetyError):
        await WebsiteEnrichmentProvider(transport=httpx.MockTransport(handler)).inspect(
            business=business(website=unsafe_url),
            website_url=unsafe_url,
        )
