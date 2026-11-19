"""Pytest Fixtures for VANTYX Backend Tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app


@pytest.fixture(scope="session")
def sync_client():
    """Synchronous test client for quick HTTP contract tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client():
    """Asynchronous httpx client for async endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
