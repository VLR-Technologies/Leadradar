import httpx

from app.core.websites import is_directory_or_social
from app.models.enrichment import SearchCandidate


class DisabledBusinessSearchProvider:
    """Safe default until an explicitly permitted search API is configured."""

    enabled = False

    def __init__(self, configured_name: str = "") -> None:
        self.configured_name = configured_name.strip()

    async def find_official_website(
        self,
        *,
        name: str,
        city: str | None,
        region: str | None,
        country: str | None,
        locality: str | None = None,
        category: str | None = None,
        phone: str | None = None,
    ) -> SearchCandidate | None:
        return None


class SearxngBusinessSearchProvider:
    """Optional adapter for a user-operated SearXNG JSON endpoint."""

    enabled = True

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client

    async def find_official_website(
        self,
        *,
        name: str,
        city: str | None,
        region: str | None,
        country: str | None,
        locality: str | None = None,
        category: str | None = None,
        phone: str | None = None,
    ) -> SearchCandidate | None:
        query = " ".join(
            part
            for part in (
                f'"{name}"',
                locality,
                city,
                region,
                country,
                category,
                f'"{phone}"' if phone else None,
                "official website",
            )
            if part
        )
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.get(
                f"{self.base_url}/search",
                params={"q": query, "format": "json", "categories": "general"},
                headers={"Accept": "application/json", "User-Agent": "LeadRadar/0.2"},
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return None
        for result in results[:10]:
            if not isinstance(result, dict) or not isinstance(result.get("url"), str):
                continue
            url = result["url"].strip()
            if is_directory_or_social(url):
                continue
            return SearchCandidate(url=url)
        return None
