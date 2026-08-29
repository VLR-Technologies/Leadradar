from typing import Annotated

from pydantic import Field

from app.models.search_session import SearchFilter
from app.schemas.base import ApiModel
from app.schemas.discovery import EnrichmentProgressResponse
from app.schemas.enrichment import EnrichBusinessResponse


class EnrichSearchSessionRequest(ApiModel):
    lead_ids: Annotated[list[str], Field(max_length=20)] | None = None
    batch_size: Annotated[int, Field(ge=1, le=20)] = 10
    retry_failed: bool = False


class EnrichSearchSessionResponse(ApiModel):
    session_id: str
    attempted: int
    results: list[EnrichBusinessResponse]
    enrichment_progress: EnrichmentProgressResponse


__all__ = [
    "EnrichSearchSessionRequest",
    "EnrichSearchSessionResponse",
    "SearchFilter",
]
