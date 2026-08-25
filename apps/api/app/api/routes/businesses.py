from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_discovery_service, get_enrichment_service
from app.models.business import Business, BusinessAddress
from app.providers.base import (
    LocationResolutionError,
    MalformedProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.schemas.business import BusinessResponse
from app.schemas.discovery import (
    DiscoverBusinessesRequest,
    DiscoverBusinessesResponse,
    DiscoveryQueryResponse,
)
from app.schemas.enrichment import (
    EnrichBusinessesBatchRequest,
    EnrichBusinessesBatchResponse,
    EnrichBusinessRequest,
    EnrichBusinessResponse,
)
from app.services.business_enrichment import (
    BusinessEnrichmentService,
    EnrichmentBatchLimitError,
)
from app.services.business_discovery import (
    BusinessDiscoveryService,
    UnsupportedCategoryError,
)
from app.services.location_resolver import LocationValidationError

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _to_business(response: BusinessResponse) -> Business:
    return Business(
        source_id=response.source_id,
        source=response.source,
        name=response.name,
        category=response.category,
        address=BusinessAddress(
            street=response.address.street,
            house_number=response.address.house_number,
            postcode=response.address.postcode,
            city=response.address.city,
            state=response.address.state,
            country=response.address.country,
            formatted=response.address.formatted,
        ),
        latitude=response.latitude,
        longitude=response.longitude,
        phone=response.phone,
        email=response.email,
        website=response.website,
        opening_hours=response.opening_hours,
    )


@router.post("/discover", response_model=DiscoverBusinessesResponse)
async def discover_businesses(
    request: DiscoverBusinessesRequest,
    service: BusinessDiscoveryService = Depends(get_discovery_service),
) -> DiscoverBusinessesResponse:
    try:
        result = await service.discover(
            country_code=request.country_code,
            region=request.region,
            city=request.city,
            category=request.category,
            limit=request.limit,
        )
    except (UnsupportedCategoryError, LocationValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except LocationResolutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ProviderTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The business data provider took too long to respond. Please try again.",
        ) from exc
    except (ProviderUnavailableError, MalformedProviderResponseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The business data provider is temporarily unavailable. Please try again.",
        ) from exc

    return DiscoverBusinessesResponse(
        query=DiscoveryQueryResponse(
            country_code=result.location.country_code,
            country=result.location.country,
            region=result.location.region,
            city=result.location.city,
            category=request.category,
            limit=request.limit,
        ),
        count=len(result.businesses),
        businesses=[
            BusinessResponse.model_validate(item)
            for item in result.businesses
        ],
    )


@router.post("/enrich", response_model=EnrichBusinessResponse)
async def enrich_business(
    request: EnrichBusinessRequest,
    service: BusinessEnrichmentService = Depends(get_enrichment_service),
) -> EnrichBusinessResponse:
    result = await service.enrich(_to_business(request.business))
    return EnrichBusinessResponse.model_validate(result)


@router.post("/enrich-batch", response_model=EnrichBusinessesBatchResponse)
async def enrich_businesses_batch(
    request: EnrichBusinessesBatchRequest,
    service: BusinessEnrichmentService = Depends(get_enrichment_service),
) -> EnrichBusinessesBatchResponse:
    try:
        results = await service.enrich_batch(
            [_to_business(business) for business in request.businesses]
        )
    except EnrichmentBatchLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return EnrichBusinessesBatchResponse(
        results=[EnrichBusinessResponse.model_validate(result) for result in results]
    )
