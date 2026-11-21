"""Orchestration Celery Background Tasks."""

from typing import Any, Dict, Optional
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.modules.orchestration.service import OrchestrationService
from app.tasks import run_task_async


@celery_app.task(bind=True, name="tasks.orchestration.run_autonomous_pipeline", max_retries=3)
def run_autonomous_pipeline_task(self, target_date: Optional[str] = None) -> Dict[str, Any]:
    """Execute the end-to-end daily autonomous pipeline for target date."""
    logger.info(f"[Celery Task] Starting autonomous pipeline execution: target_date={target_date}")
    try:
        async def _run(db):
            run = await OrchestrationService.run_daily_autonomous_pipeline(db, target_date=target_date)
            return {
                "workflow_run_id": run.id,
                "workflow_name": run.workflow_name,
                "status": run.status,
                "published_count": run.published_count,
            }
        return run_task_async(_run)
    except Exception as exc:
        logger.error(f"[Celery Task] Pipeline execution failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, name="tasks.orchestration.run_daily_pipeline")
def run_daily_pipeline_task(self) -> Dict[str, Any]:
    """Scheduled trigger from Celery Beat at 06:00 IST daily."""
    logger.info("[Celery Beat] Triggering scheduled daily pipeline execution")
    return run_autonomous_pipeline_task(target_date=None)
