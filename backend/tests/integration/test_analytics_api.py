"""Integration tests for VANTYX Analytics API Endpoints."""

import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_overview_and_bootstrap(async_client: AsyncClient):
    """Verify GET /api/v1/analytics/overview returns valid channel benchmarks."""
    response = await async_client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()

    assert "channel_name" in data
    assert data["channel_name"] in ["Astro Rebel", "VANTYX Primary Channel"]
    assert "total_views" in data
    assert "total_videos" in data
    assert "average_view_percentage" in data
    assert "history_trend" in data
    assert isinstance(data["history_trend"], list)


@pytest.mark.asyncio
async def test_analytics_collection_and_jobs_listing(async_client: AsyncClient):
    """Verify POST /api/v1/analytics/collect triggers sweep and logs job record."""
    collect_res = await async_client.post("/api/v1/analytics/collect")
    assert collect_res.status_code == 200
    job_data = collect_res.json()

    assert job_data["status"] == "completed"
    assert job_data["job_id"].startswith("job_analytics_")
    assert job_data["errors_count"] == 0

    # Query jobs list
    jobs_res = await async_client.get("/api/v1/analytics/jobs")
    assert jobs_res.status_code == 200
    jobs_list = jobs_res.json()
    assert len(jobs_list) >= 1
    assert any(j["job_id"] == job_data["job_id"] for j in jobs_list)


@pytest.mark.asyncio
async def test_published_videos_performance_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/analytics/videos returns granular video performance."""
    response = await async_client.get("/api/v1/analytics/videos")
    assert response.status_code == 200
    videos = response.json()
    assert isinstance(videos, list)
    if videos:
        v = videos[0]
        assert "schedule_id" in v
        assert "views" in v
        assert "average_view_percentage" in v
        assert "relative_retention_index" in v
        assert "category" in v
        assert "duration_bucket" in v


@pytest.mark.asyncio
async def test_performance_intelligence_insights_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/analytics/insights returns multidimensional statistical reports."""
    response = await async_client.get("/api/v1/analytics/insights")
    assert response.status_code == 200
    insights = response.json()

    assert "duration_insights" in insights
    assert "category_insights" in insights
    assert "slot_insights" in insights
    assert "hook_insights" in insights
    assert "correlation_vs_causation_notice" in insights
    assert "STATISTICAL METHODOLOGY NOTE" in insights["correlation_vs_causation_notice"]
    assert "overall_confidence" in insights

    # Check structure of duration buckets
    durations = [d["key"] for d in insights["duration_insights"]]
    assert "15-25s" in durations
    assert "25-35s" in durations
    assert "35-45s" in durations
    assert "45-60s" in durations

    for bucket in insights["duration_insights"]:
        assert "confidence_level" in bucket
        assert bucket["confidence_level"] in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_feedback_engine_configuration_and_status(async_client: AsyncClient):
    """Verify toggling feedback engine and updating max_impact parameter."""
    # 1. Update config
    patch_res = await async_client.patch(
        "/api/v1/analytics/feedback/config",
        json={"feedback_enabled": True, "max_impact": 0.12, "min_sample_size": 2},
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["feedback_enabled"] is True
    assert patch_data["max_impact"] == 0.12
    assert patch_data["min_sample_size"] == 2

    # 2. Verify status
    status_res = await async_client.get("/api/v1/analytics/feedback/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["feedback_enabled"] is True
    assert status_data["max_impact"] == 0.12
    assert "category_multipliers" in status_data
    assert "duration_multipliers" in status_data
