import logging
import re
from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_discovery_service,
    get_enrichment_service,
    get_search_session_store,
    get_supabase_persistence_service,
)
from app.core.config import get_settings
from app.db.supabase import SupabasePersistenceError, SupabasePersistenceService
from app.models.business import (
    Business,
    BusinessAddress,
    FieldProvenance,
    WebsiteAudit,
)
from app.models.enrichment import EnrichmentResult
from app.models.search_session import SearchSession
from app.providers.base import (
    AllProvidersFailedError,
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
    ProviderStatusResponse,
)
from app.schemas.enrichment import (
    EnrichBusinessesBatchRequest,
    EnrichBusinessesBatchResponse,
    EnrichBusinessRequest,
    EnrichBusinessResponse,
)
from app.schemas.export import ExportBusinessesRequest
from app.schemas.search_session import (
    EnrichSearchSessionRequest,
    EnrichSearchSessionResponse,
    SearchFilter,
)
from app.services.business_discovery import (
    BusinessDiscoveryService,
    UnsupportedCategoryError,
)
from app.services.business_enrichment import (
    BusinessEnrichmentService,
    EnrichmentBatchLimitError,
)
from app.services.excel_export import build_leads_workbook
from app.services.location_resolver import LocationValidationError
from app.services.search_sessions import (
    SearchSessionCapacityError,
    SearchSessionNotFoundError,
    SearchSessionStore,
    apply_enrichment_result,
    enrichment_progress,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])
logger = logging.getLogger(__name__)
DiscoveryService = Annotated[
    BusinessDiscoveryService,
    Depends(get_discovery_service),
]
EnrichmentService = Annotated[
    BusinessEnrichmentService,
    Depends(get_enrichment_service),
]
SessionStore = Annotated[SearchSessionStore, Depends(get_search_session_store)]
PersistenceService = Annotated[
    SupabasePersistenceService,
    Depends(get_supabase_persistence_service),
]
_PERSISTENCE_WARNING = (
    "Lead results were returned, but persistent storage is currently unavailable."
)


def _to_business(response: BusinessResponse) -> Business:
    values = {
        "source_id": response.source_id,
        "source": response.source,
        "name": response.name,
        "category": response.category,
        "address": BusinessAddress(
            street=response.address.street,
            house_number=response.address.house_number,
            postcode=response.address.postcode,
            locality=response.address.locality,
            district=response.address.district,
            city=response.address.city,
            state=response.address.state,
            country=response.address.country,
            formatted=response.address.formatted,
        ),
        "latitude": response.latitude,
        "longitude": response.longitude,
        "phone": response.phone,
        "email": response.email,
        "website": response.website,
        "opening_hours": response.opening_hours,
        "lead_id": response.lead_id,
        "subcategories": tuple(response.subcategories),
        "phones": tuple(response.phones),
        "normalized_phones": tuple(response.normalized_phones),
        "emails": tuple(response.emails),
        "websites": tuple(response.websites),
        "website_status": response.website_status,
        "website_type": response.website_type,
        "directory_links": tuple(response.directory_links),
        "social_links": tuple(response.social_links),
        "whatsapp_number": response.whatsapp_number,
        "whatsapp_numbers": tuple(response.whatsapp_numbers),
        "rating": response.rating,
        "review_count": response.review_count,
        "rating_source": response.rating_source,
        "confidence": response.confidence,
        "sources": tuple(response.sources) or (response.source,),
        "source_ids": {key: tuple(value) for key, value in response.source_ids.items()},
        "field_provenance": {
            key: tuple(
                FieldProvenance(
                    value=item.value,
                    source=item.source,
                    confidence=item.confidence,
                    source_url=item.source_url,
                    source_type=item.source_type,
                )
                for item in items
            )
            for key, items in response.field_provenance.items()
        },
        "enrichment_status": response.enrichment_status,
        "website_audit": (
            WebsiteAudit(**response.website_audit.model_dump()) if response.website_audit else None
        ),
        "lead_score": response.lead_score,
        "opportunity_level": response.opportunity_level,
        "opportunity_reasons": tuple(response.opportunity_reasons),
        "operating_status": response.operating_status,
    }
    if response.scraped_at is not None:
        values["scraped_at"] = response.scraped_at
    return Business(**values)


@router.post("/discover", response_model=DiscoverBusinessesResponse)
async def discover_businesses(
    request: DiscoverBusinessesRequest,
    service: DiscoveryService,
    sessions: SessionStore,
    persistence: PersistenceService,
) -> DiscoverBusinessesResponse:
    effective_limit = (
        get_settings().discovery_max_limit if request.limit == "all" else request.limit
    )
    try:
        result = await service.discover(
            country_code=request.country_code,
            region=request.region,
            city=request.city,
            category=request.category,
            limit=effective_limit,
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
    except AllProvidersFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
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

    try:
        session = sessions.create(
            result=result,
            category=request.category,
            requested_limit=request.limit,
            effective_limit=effective_limit,
        )
    except SearchSessionCapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    await _persist_search_session(persistence, session)
    page = sessions.page(
        session.session_id,
        page=1,
        page_size=request.page_size,
        filter_name="all",
    )
    return _session_page_response(page)


def _session_page_response(page) -> DiscoverBusinessesResponse:
    session = page.session
    return DiscoverBusinessesResponse(
        query=DiscoveryQueryResponse(
            country_code=session.location.country_code,
            country=session.location.country,
            region=session.location.region,
            city=session.location.city,
            category=session.category,
            limit=session.requested_limit,
        ),
        count=len(page.businesses),
        businesses=[BusinessResponse.model_validate(item) for item in page.businesses],
        providers=[ProviderStatusResponse.model_validate(item) for item in session.providers],
        warnings=list(session.warnings),
        session_id=session.session_id,
        page=page.page,
        page_size=page.page_size,
        total_count=page.total_count,
        total_pages=page.total_pages,
        effective_limit=session.effective_limit,
        summary=page.summary,
        enrichment_progress=page.enrichment_progress,
        expires_at=session.expires_at,
    )


@router.get("/search-sessions/{session_id}", response_model=DiscoverBusinessesResponse)
async def get_search_session_page(
    session_id: str,
    sessions: SessionStore,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=25, le=100)] = 50,
    filter_name: Annotated[SearchFilter, Query(alias="filter")] = "all",
) -> DiscoverBusinessesResponse:
    try:
        result = sessions.page(
            session_id,
            page=page,
            page_size=page_size,
            filter_name=filter_name,
        )
    except SearchSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _session_page_response(result)


@router.post(
    "/search-sessions/{session_id}/enrich",
    response_model=EnrichSearchSessionResponse,
)
async def enrich_search_session(
    session_id: str,
    request: EnrichSearchSessionRequest,
    service: EnrichmentService,
    sessions: SessionStore,
    persistence: PersistenceService,
) -> EnrichSearchSessionResponse:
    try:
        _, businesses = sessions.enrichment_candidates(
            session_id,
            lead_ids=set(request.lead_ids) if request.lead_ids else None,
            batch_size=request.batch_size,
            retry_failed=request.retry_failed,
        )
    except SearchSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    results = await service.enrich_batch(businesses) if businesses else []
    session = sessions.apply_enrichment_results(session_id, results)
    await _persist_enrichment(
        persistence,
        session,
        source_ids={result.source_id for result in results},
        enrichment_results=results,
    )
    return EnrichSearchSessionResponse(
        session_id=session_id,
        attempted=len(businesses),
        results=[EnrichBusinessResponse.model_validate(result) for result in results],
        enrichment_progress=enrichment_progress(session.businesses),
    )


@router.get("/search-sessions/{session_id}/export")
async def export_search_session(
    session_id: str,
    sessions: SessionStore,
    filter_name: Annotated[SearchFilter, Query(alias="filter")] = "all",
) -> StreamingResponse:
    try:
        session, businesses = sessions.filtered(session_id, filter_name)
    except SearchSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not businesses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No businesses match the selected export filter.",
        )
    return _workbook_response(
        [BusinessResponse.model_validate(value) for value in businesses],
        f"{session.location.city}-{session.category}-{filter_name}",
    )


@router.post("/enrich", response_model=EnrichBusinessResponse)
async def enrich_business(
    request: EnrichBusinessRequest,
    service: EnrichmentService,
    persistence: PersistenceService,
) -> EnrichBusinessResponse:
    business = _to_business(request.business)
    result = await service.enrich(business)
    await _persist_businesses(
        persistence,
        [apply_enrichment_result(business, result)],
        enrichment_results=[result],
    )
    return EnrichBusinessResponse.model_validate(result)


@router.post("/enrich-batch", response_model=EnrichBusinessesBatchResponse)
async def enrich_businesses_batch(
    request: EnrichBusinessesBatchRequest,
    service: EnrichmentService,
    persistence: PersistenceService,
) -> EnrichBusinessesBatchResponse:
    businesses = [_to_business(business) for business in request.businesses]
    try:
        results = await service.enrich_batch(businesses)
    except EnrichmentBatchLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    result_by_source = {result.source_id: result for result in results}
    await _persist_businesses(
        persistence,
        [
            apply_enrichment_result(business, result_by_source[business.source_id])
            for business in businesses
            if business.source_id in result_by_source
        ],
        enrichment_results=results,
    )
    return EnrichBusinessesBatchResponse(
        results=[EnrichBusinessResponse.model_validate(result) for result in results]
    )


@router.post("/export")
async def export_businesses(request: ExportBusinessesRequest) -> StreamingResponse:
    return _workbook_response(request.businesses, request.search_label or "leads")


def _workbook_response(
    businesses: list[BusinessResponse],
    search_label: str,
) -> StreamingResponse:
    payload = build_leads_workbook(businesses)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    label = re.sub(r"[^a-z0-9]+", "-", search_label.casefold()).strip("-")
    filename = f"leadradar-{label or 'leads'}-{timestamp}.xlsx"
    logger.info(
        "export.complete",
        extra={"count": len(businesses), "bytes": len(payload)},
    )
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _add_persistence_warning(session: SearchSession) -> None:
    if _PERSISTENCE_WARNING not in session.warnings:
        session.warnings = (*session.warnings, _PERSISTENCE_WARNING)


async def _persist_search_session(
    persistence: SupabasePersistenceService,
    session: SearchSession,
) -> None:
    try:
        await persistence.persist_search_session(session)
    except SupabasePersistenceError:
        logger.exception(
            "supabase.persistence_failed",
            extra={"operation": "discovery", "session_id": session.session_id},
        )
        _add_persistence_warning(session)


async def _persist_enrichment(
    persistence: SupabasePersistenceService,
    session: SearchSession,
    *,
    source_ids: set[str],
    enrichment_results: list[EnrichmentResult],
) -> None:
    try:
        await persistence.persist_enrichment(
            session,
            source_ids=source_ids,
            enrichment_results=enrichment_results,
        )
    except SupabasePersistenceError:
        logger.exception(
            "supabase.persistence_failed",
            extra={"operation": "enrichment", "session_id": session.session_id},
        )
        _add_persistence_warning(session)


async def _persist_businesses(
    persistence: SupabasePersistenceService,
    businesses: list[Business],
    *,
    enrichment_results: list[EnrichmentResult],
) -> None:
    try:
        await persistence.persist_businesses(
            businesses,
            enrichment_results=enrichment_results,
        )
    except SupabasePersistenceError:
        logger.exception(
            "supabase.persistence_failed",
            extra={"operation": "standalone_enrichment"},
        )
