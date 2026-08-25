from typing import Protocol

from app.core.categories import BusinessCategory
from app.models.business import Business
from app.models.location import ResolvedLocation


class ProviderError(Exception):
    """Base error for business data providers."""


class ProviderTimeoutError(ProviderError):
    """The upstream provider timed out."""


class ProviderUnavailableError(ProviderError):
    """The upstream provider was unavailable or rejected the request."""


class MalformedProviderResponseError(ProviderError):
    """The upstream provider returned an unusable payload."""


class LocationResolutionError(ProviderError):
    """The provider could not resolve the location to a safe search area."""


class BusinessProvider(Protocol):
    async def discover(
        self,
        *,
        location: ResolvedLocation,
        category: BusinessCategory,
        limit: int,
    ) -> list[Business]: ...
