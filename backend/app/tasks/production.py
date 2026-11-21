"""Video Production Celery Background Tasks."""

from typing import Any, Dict, Optional
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.modules.production.service import ProductionService
from app.schemas.production import RenderSettingsInput
from app.tasks import run_task_async


@celery_app.task(bind=True, name="tasks.production.render_clip", max_retries=2)
def render_clip_task(
    self,
    candidate_id: int,
    settings_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute 9:16 vertical video rendering for candidate clip in background."""
    logger.info(f"[Celery Task] Rendering clip candidate #{candidate_id}")
    try:
        render_settings = RenderSettingsInput(**(settings_dict or {}))

        async def _run(db):
            job = await ProductionService.execute_render(
                db=db,
                candidate_id=candidate_id,
                render_settings=render_settings,
            )
            return {
                "job_id": job.id,
                "candidate_id": job.candidate_id,
                "status": job.status,
                "output_file_path": job.output_file_path,
                "is_synthetic": job.is_synthetic,
            }
        return run_task_async(_run)
    except Exception as exc:
        logger.error(f"[Celery Task] Clip render failed for candidate #{candidate_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)
