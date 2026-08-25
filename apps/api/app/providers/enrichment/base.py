from typing import Protocol

from app.models.business import Business
from app.models.enrichment import SearchCandidate, WebsiteInspection


class EnrichmentProviderError(Exception):
    """Base exception for a bounded enrichment provider failure."""


class WebsiteTimeoutError(EnrichmentProviderError):
    """The official website did not respond within the configured timeout."""


class WebsiteUnavailableError(EnrichmentProviderError):
    """The official website could not be reached or returned unusable content."""


class WebsiteDnsError(WebsiteUnavailableError):
    """The official website hostname could not be resolved."""


class WebsiteAccessDeniedError(EnrichmentProviderError):
    """The official website explicitly refused automated access."""


class WebsiteParserError(EnrichmentProviderError):
    """The official website response could not be parsed safely."""


class WebsiteSafetyError(EnrichmentProviderError):
    """The candidate URL was unsafe or left the permitted website boundary."""


class RobotsDisallowedError(EnrichmentProviderError):
    """The website explicitly disallows the requested automated inspection."""


class OfficialWebsiteEnrichmentProvider(Protocol):
    async def inspect(self, *, business: Business, website_url: str) -> WebsiteInspection: ...


class BusinessSearchProvider(Protocol):
    enabled: bool

    async def find_official_website(
        self,
        *,
        name: str,
        city: str | None,
        region: str | None,
        country: str | None,
    ) -> SearchCandidate | None: ...
