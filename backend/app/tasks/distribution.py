"""YouTube Distribution Celery Background Tasks."""

from typing import Any, Dict
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.modules.distribution.service import DistributionService
from app.tasks import run_task_async


@celery_app.task(bind=True, name="tasks.distribution.publish_slot", max_retries=3)
def publish_slot_task(self, schedule_id: int, force_mock: bool = False) -> Dict[str, Any]:
    """Execute scheduled YouTube Shorts upload and release."""
    logger.info(f"[Celery Task] Publishing Short schedule #{schedule_id}")
    try:
        async def _run(db):
            schedule = await DistributionService.execute_publishing_upload(
                db=db,
                schedule_id=schedule_id,
                force_mock=force_mock,
            )
            return {
                "schedule_id": schedule.id,
                "status": schedule.status,
                "youtube_video_id": schedule.youtube_video_id,
                "publish_url": schedule.publish_url,
                "is_mock": schedule.is_mock,
            }
        return run_task_async(_run)
    except Exception as exc:
        logger.error(f"[Celery Task] Publishing failed for schedule #{schedule_id}: {exc}")
        raise self.retry(exc=exc, countdown=120)
