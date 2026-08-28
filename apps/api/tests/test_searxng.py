import httpx
import pytest

from app.providers.enrichment.search import SearxngBusinessSearchProvider


@pytest.mark.asyncio
async def test_searxng_returns_first_non_directory_candidate() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert "ABC Dental" in request.url.params["q"]
        return httpx.Response(
            200,
            json={
                "results": [
                    {"url": "https://www.justdial.com/Hyderabad/abc"},
                    {"url": "https://abcdental.in/contact"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SearxngBusinessSearchProvider(
            base_url="http://searxng.local",
            client=client,
        )
        candidate = await provider.find_official_website(
            name="ABC Dental",
            city="Hyderabad",
            region="Telangana",
            country="India",
        )

    assert candidate is not None
    assert candidate.url == "https://abcdental.in/contact"
    assert candidate.confidence == "low"


@pytest.mark.asyncio
async def test_searxng_ignores_malformed_results() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [None, {"title": "No URL"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SearxngBusinessSearchProvider(
            base_url="http://searxng.local",
            client=client,
        )
        candidate = await provider.find_official_website(
            name="ABC Dental",
            city="Hyderabad",
            region=None,
            country="India",
        )

    assert candidate is None
