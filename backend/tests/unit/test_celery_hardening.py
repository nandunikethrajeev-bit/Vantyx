"""Unit tests for Celery background tasks registration and health monitoring."""

import pytest
from app.core.celery_app import celery_app, check_celery_worker_availability


def test_celery_tasks_registered():
    """Verify all 5 core background tasks are properly registered with Celery."""
    tasks = celery_app.tasks.keys()
    assert "tasks.orchestration.run_autonomous_pipeline" in tasks
    assert "tasks.orchestration.run_daily_pipeline" in tasks
    assert "tasks.production.render_clip" in tasks
    assert "tasks.distribution.publish_slot" in tasks
    assert "tasks.analytics.collect_analytics" in tasks


def test_celery_worker_availability_check():
    """Verify worker health inspection helper returns structured health object."""
    info = check_celery_worker_availability()
    assert "status" in info
    assert "message" in info
    assert "worker_count" in info
    assert info["status"] in ("eager_development", "healthy", "unreachable")


def test_celery_beat_schedule_configured():
    """Verify daily recurring pipeline is scheduled in Celery Beat."""
    beat = celery_app.conf.beat_schedule
    assert "vantyx-daily-autonomous-pipeline" in beat
    assert beat["vantyx-daily-autonomous-pipeline"]["task"] == "tasks.orchestration.run_daily_pipeline"
