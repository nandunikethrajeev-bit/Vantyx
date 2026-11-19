"""Integration tests for VANTYX API health endpoints and error responses."""

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient


def test_root_endpoint(sync_client: TestClient):
    """Verify root discovery endpoint."""
    response = sync_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VANTYX"
    assert data["status"] == "operational"
    assert "version" in data


def test_liveness_endpoint(sync_client: TestClient):
    """Verify GET /api/v1/health liveness probe."""
    response = sync_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "VANTYX"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/health/ready readiness probe."""
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert "database" in data["components"]
    assert "status" in data["components"]["database"]
    assert "message" in data["components"]["database"]


def test_standardized_404_error(sync_client: TestClient):
    """Verify non-existent endpoints return standardized ErrorResponse structure."""
    response = sync_client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"


def test_cors_headers(sync_client: TestClient):
    """Verify CORS middleware exposes proper headers on allowed origins."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = sync_client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
