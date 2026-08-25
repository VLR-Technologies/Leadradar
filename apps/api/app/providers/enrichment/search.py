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
    ) -> SearchCandidate | None:
        return None
