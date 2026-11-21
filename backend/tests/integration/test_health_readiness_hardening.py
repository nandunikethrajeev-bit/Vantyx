"""Integration tests for enhanced /api/v1/health/ready readiness probe."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_comprehensive_readiness_probe(async_client: AsyncClient):
    """Verify readiness endpoint evaluates all 6 subsystem components."""
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert "components" in data

    components = data["components"]
    expected_components = [
        "database",
        "redis",
        "celery_worker",
        "youtube_oauth",
        "ai_provider",
        "storage",
    ]
    for comp in expected_components:
        assert comp in components, f"Missing component {comp} in readiness response"
        assert "status" in components[comp]
        assert "message" in components[comp]

    assert components["database"]["status"] == "healthy"
    assert components["storage"]["status"] in ("healthy", "degraded")
