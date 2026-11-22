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


def test_local_task_execution_mode_configuration():
    """Verify local in-process execution mode is recognized and configured."""
    from app.core.config import Settings
    dev_cfg = Settings(TASK_EXECUTION_MODE="inprocess", ENVIRONMENT="development")
    assert dev_cfg.is_local_task_execution is True

    eager_cfg = Settings(TASK_EXECUTION_MODE="eager", ENVIRONMENT="development")
    assert eager_cfg.is_local_task_execution is True

    dist_cfg = Settings(TASK_EXECUTION_MODE="distributed", ENVIRONMENT="development")
    assert dist_cfg.is_local_task_execution is False


def test_production_mode_rejects_inprocess_execution():
    """Verify production strictly forbids in-process/eager task execution modes."""
    from app.core.config import Settings

    prod_inprocess = Settings(
        ENVIRONMENT="production",
        TASK_EXECUTION_MODE="inprocess",
        CELERY_ALWAYS_EAGER=False,
    )
    with pytest.raises(RuntimeError, match="In-process/eager task execution mode is strictly prohibited"):
        prod_inprocess.verify_production_safeguards()

    prod_eager = Settings(
        ENVIRONMENT="production",
        TASK_EXECUTION_MODE="distributed",
        CELERY_ALWAYS_EAGER=True,
    )
    with pytest.raises(RuntimeError, match="In-process/eager task execution mode is strictly prohibited"):
        prod_eager.verify_production_safeguards()


def test_production_mode_accepts_distributed_execution():
    """Verify production accepts distributed task execution configuration."""
    from app.core.config import Settings

    prod_dist = Settings(
        ENVIRONMENT="production",
        TASK_EXECUTION_MODE="distributed",
        CELERY_ALWAYS_EAGER=False,
    )
    # verify_production_safeguards does not raise when distributed is correctly configured
    prod_dist.verify_production_safeguards()
    assert prod_dist.is_production is True
    assert prod_dist.is_local_task_execution is False
