from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_call_log_store
from app.core.config import Settings, get_settings
from app.services.call_log import CallLogStore

router = APIRouter(tags=["calls"])


class CallDecisionRequest(BaseModel):
    lead_key: str = Field(min_length=1, max_length=200)
    business_name: str = Field(default="", max_length=300)
    phone: str = Field(default="", max_length=50)
    decision: Literal["yes", "no"]


def require_admin_key(
    x_admin_key: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access is not configured.",
        )
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key.",
        )


@router.post("/calls", status_code=status.HTTP_204_NO_CONTENT)
def record_call(
    payload: CallDecisionRequest,
    store: CallLogStore = Depends(get_call_log_store),
) -> None:
    store.record(
        lead_key=payload.lead_key,
        business_name=payload.business_name,
        phone=payload.phone,
        decision=payload.decision,
    )


@router.get("/admin/calls", dependencies=[Depends(require_admin_key)])
def admin_calls(
    store: CallLogStore = Depends(get_call_log_store),
) -> dict:
    return {
        "summary": store.summary(),
        "recent": store.recent(limit=200),
    }


@router.post("/admin/calls/purge", dependencies=[Depends(require_admin_key)])
def admin_purge(
    days: int = 4,
    store: CallLogStore = Depends(get_call_log_store),
) -> dict:
    if days < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days must be at least 1.",
        )
    return {"deleted": store.purge_older_than(days)}