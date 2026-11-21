"""Analytics Collection Celery Background Tasks."""

from typing import Any, Dict
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.modules.analytics.service import AnalyticsService
from app.tasks import run_task_async


@celery_app.task(bind=True, name="tasks.analytics.collect_analytics", max_retries=2)
def collect_analytics_task(self, lookback_days: int = 30) -> Dict[str, Any]:
    """Execute scheduled YouTube Analytics collection and feedback computation."""
    logger.info(f"[Celery Task] Collecting YouTube analytics (lookback={lookback_days}d)")
    try:
        async def _run(db):
            job = await AnalyticsService.run_analytics_collection(db=db, lookback_days=lookback_days)
            return {
                "job_id": job.id,
                "status": job.status,
                "videos_processed": job.videos_processed,
                "snapshots_collected": job.snapshots_collected,
                "is_mock": job.is_mock,
            }
        return run_task_async(_run)
    except Exception as exc:
        logger.error(f"[Celery Task] Analytics collection failed: {exc}")
        raise self.retry(exc=exc, countdown=300)
