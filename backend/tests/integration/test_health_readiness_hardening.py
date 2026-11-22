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
    assert data["execution_mode"] in ("LOCAL IN-PROCESS", "DISTRIBUTED CELERY")


@pytest.mark.asyncio
async def test_local_runtime_truthfulness_and_redis_offline_reporting(async_client: AsyncClient):
    """Verify runtime truthfully reports LOCAL IN-PROCESS and never falsely reports Redis as online."""
    # Test Liveness
    live_resp = await async_client.get("/api/v1/health")
    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert live_data["execution_mode"] == "LOCAL IN-PROCESS"

    # Test Readiness
    ready_resp = await async_client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert ready_data["execution_mode"] == "LOCAL IN-PROCESS"

    comps = ready_data["components"]

    # When Redis is not running locally, it must report offline, never healthy!
    import redis
    from app.core.config import settings
    real_redis_up = False
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.1, socket_timeout=0.1)
        r.ping()
        real_redis_up = True
    except Exception:
        real_redis_up = False

    if not real_redis_up:
        assert comps["redis"]["status"] == "offline"
        assert "offline" in comps["redis"]["message"].lower()
        assert comps["redis"]["latency_ms"] is None

    # In local in-process mode, worker status is eager_development
    assert comps["celery_worker"]["status"] == "eager_development"
    assert "in-process" in comps["celery_worker"]["message"].lower()

    # AI provider transparency
    if not settings.GEMINI_API_KEY:
        assert comps["ai_provider"]["status"] == "heuristic_fallback"
        assert "heuristic" in comps["ai_provider"]["message"].lower()
