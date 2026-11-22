"""Celery Worker & Background Job Configuration for VANTYX.

Provides asynchronous task distribution with graceful in-process eager fallback
when Redis or standalone worker daemons are not running in development,
while enforcing strict distributed broker requirements in production.
"""

from typing import Any, Dict
from celery import Celery
from celery.schedules import crontab
import redis

from app.core.config import settings
from app.core.logging import logger

# Check Redis availability safely with quick timeout probe
is_redis_available = False
if not settings.is_local_task_execution or settings.is_production:
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
        r.ping()
        is_redis_available = True
    except Exception:
        is_redis_available = False

# Enforce strict production safeguards against development-only execution modes
if settings.is_production:
    settings.verify_production_safeguards()
    if not is_redis_available:
        raise RuntimeError(
            f"Redis broker connection required for Celery in production mode. Unreachable at {settings.REDIS_URL}"
        )

# Determine background task execution mode
eager_mode = (
    settings.is_local_task_execution
    or settings.CELERY_ALWAYS_EAGER
    or not is_redis_available
) and not settings.is_production

# Initialize Celery Application
celery_app = Celery(
    "vantyx",
    broker=settings.CELERY_BROKER_URL if (is_redis_available and not eager_mode) else "memory://",
    backend=settings.CELERY_RESULT_BACKEND if (is_redis_available and not eager_mode) else "cache+memory://",
)

# Parse daily run time (e.g. "06:00")
run_hour, run_minute = 6, 0
if settings.DAILY_PIPELINE_RUN_TIME and ":" in settings.DAILY_PIPELINE_RUN_TIME:
    parts = settings.DAILY_PIPELINE_RUN_TIME.split(":")
    run_hour = int(parts[0])
    run_minute = int(parts[1]) if len(parts) > 1 else 0

celery_app.conf.update(
    task_always_eager=eager_mode,
    task_eager_propagates=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    worker_concurrency=settings.MAX_CONCURRENT_RENDERS,
    task_track_started=True,
    task_time_limit=900,  # 15 minutes max per video processing task
    beat_schedule={
        "vantyx-daily-autonomous-pipeline": {
            "task": "tasks.orchestration.run_daily_pipeline",
            "schedule": crontab(hour=run_hour, minute=run_minute),
            "options": {"queue": "orchestration"},
        },
        "vantyx-daily-analytics-collection": {
            "task": "tasks.analytics.collect_analytics",
            "schedule": crontab(hour=(run_hour + 1) % 24, minute=run_minute),
            "options": {"queue": "analytics"},
        },
    },
)

# Register background tasks across modular domains
import app.tasks.orchestration  # noqa: F401
import app.tasks.production     # noqa: F401
import app.tasks.distribution   # noqa: F401
import app.tasks.analytics      # noqa: F401


def check_celery_worker_availability() -> Dict[str, Any]:
    """Inspect Celery worker connectivity and return structured health details."""
    if eager_mode or settings.is_local_task_execution:
        return {
            "status": "eager_development",
            "message": "Local in-process execution active (Celery tasks execute in-process without distributed workers)",
            "workers": [],
            "worker_count": 0,
        }
    try:
        inspector = celery_app.control.inspect(timeout=0.5)
        ping_res = inspector.ping() if inspector else None
        if ping_res and len(ping_res) > 0:
            workers = list(ping_res.keys())
            return {
                "status": "healthy",
                "message": f"Active distributed Celery workers: {len(workers)}",
                "workers": workers,
                "worker_count": len(workers),
            }
        return {
            "status": "unreachable",
            "message": "No active Celery worker processes responding to heartbeat probe",
            "workers": [],
            "worker_count": 0,
        }
    except Exception as exc:
        return {
            "status": "unreachable",
            "message": f"Worker inspection error: {type(exc).__name__}",
            "workers": [],
            "worker_count": 0,
        }


logger.info(
    f"Celery initialized: mode={'EAGER (In-process)' if eager_mode else 'DISTRIBUTED (Redis)'}, "
    f"Redis ping={'OK' if is_redis_available else 'OFFLINE'}"
)
