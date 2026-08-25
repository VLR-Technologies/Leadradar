from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import app


@pytest.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

