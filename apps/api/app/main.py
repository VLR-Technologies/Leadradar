import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_call_log_store
from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()


async def _purge_call_log_periodically() -> None:
    store = get_call_log_store()
    while True:
        with contextlib.suppress(Exception):
            store.purge_older_than(settings.call_log_retention_days)
        await asyncio.sleep(settings.call_log_cleanup_interval_seconds)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_purge_call_log_periodically())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.app_version,
    description="Business discovery API for VLR Technologies' Lead Radar.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Admin-Key"],
    expose_headers=["Content-Disposition"],
)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}