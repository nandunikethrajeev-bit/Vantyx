"""Celery Worker & Background Job Configuration for VANTYX.

Provides asynchronous task distribution with graceful in-process eager fallback
when Redis or standalone worker daemons are not running.
"""

from typing import Any, Dict
from celery import Celery
import redis

from app.core.config import settings
from app.core.logging import logger

# Check Redis availability safely with quick timeout probe
is_redis_available = False
try:
    r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
    r.ping()
    is_redis_available = True
except Exception:
    is_redis_available = False

# Initialize Celery Application
celery_app = Celery(
    "vantyx",
    broker=settings.CELERY_BROKER_URL if is_redis_available else "memory://",
    backend=settings.CELERY_RESULT_BACKEND if is_redis_available else "cache+memory://",
)

# Apply configuration
eager_mode = settings.CELERY_ALWAYS_EAGER or not is_redis_available

celery_app.conf.update(
    task_always_eager=eager_mode,
    task_eager_propagates=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    worker_concurrency=settings.MAX_CONCURRENT_RENDERS,
    task_track_started=True,
    task_time_limit=900,  # 15 minutes max per video processing task
)

logger.info(
    f"Celery initialized: mode={'EAGER (In-process)' if eager_mode else 'DISTRIBUTED (Redis)'}, "
    f"Redis ping={'OK' if is_redis_available else 'OFFLINE'}"
)
