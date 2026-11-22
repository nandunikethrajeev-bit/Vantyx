"""VANTYX Health Check Endpoints.

Provides /health for basic service liveness and /health/ready for
verifying dependency readiness (database connectivity, Redis, Celery, AI, OAuth, disk storage).
"""

import os
import shutil
import time
from datetime import datetime, timezone
from fastapi import APIRouter, status
import redis

from app.core.celery_app import check_celery_worker_availability
from app.core.config import settings
from app.db.session import check_db_connectivity, get_async_session_maker
from app.schemas.health import ComponentHealth, HealthResponse, ReadinessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Returns basic liveness and application runtime metadata.",
)
async def liveness_probe() -> HealthResponse:
    """Check basic API liveness."""
    mode_str = "LOCAL IN-PROCESS" if settings.is_local_task_execution else "DISTRIBUTED CELERY"
    return HealthResponse(
        status="ok",
        app=settings.PROJECT_NAME,
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        execution_mode=mode_str,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Probes internal dependencies (PostgreSQL, Redis, Celery, Storage, External APIs) to verify overall readiness.",
)
async def readiness_probe() -> ReadinessResponse:
    """Check readiness of all system dependencies and external integration boundaries."""
    # 1. Database Connectivity
    start_time = time.perf_counter()
    is_db_connected, db_message = await check_db_connectivity()
    db_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    db_health = ComponentHealth(
        status="healthy" if is_db_connected else "unreachable",
        message=db_message,
        latency_ms=db_latency_ms if is_db_connected else None,
    )

    # 2. Redis Cache & Queue Broker
    redis_start = time.perf_counter()
    real_redis_connected = False
    redis_latency = None
    redis_err_msg = None
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
        r.ping()
        real_redis_connected = True
        redis_latency = round((time.perf_counter() - redis_start) * 1000, 2)
    except Exception as exc:
        redis_err_msg = type(exc).__name__

    if real_redis_connected:
        redis_health = ComponentHealth(
            status="healthy",
            message=f"Redis broker online at {settings.REDIS_URL}",
            latency_ms=redis_latency,
        )
    else:
        # NEVER report Redis as healthy or online unless a real connection succeeds
        if settings.is_local_task_execution and not settings.is_production:
            redis_health = ComponentHealth(
                status="offline",
                message=f"Redis broker offline ({redis_err_msg or 'Unreachable'}). Not required for local in-process execution.",
                latency_ms=None,
            )
        else:
            redis_health = ComponentHealth(
                status="unreachable" if settings.is_production else "degraded",
                message=f"Redis broker offline ({redis_err_msg or 'Unreachable'}).",
                latency_ms=None,
            )

    # 3. Celery Worker Pool
    worker_info = check_celery_worker_availability()
    worker_health = ComponentHealth(
        status=worker_info["status"],
        message=worker_info["message"],
        latency_ms=None,
    )

    # 4. YouTube OAuth Integration Status
    oauth_configured = bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET)
    oauth_msg = (
        "OAuth credentials configured (Client ID active)"
        if oauth_configured
        else "OAuth credentials missing (Mock publishing active for offline validation)"
    )
    oauth_health = ComponentHealth(
        status="healthy" if oauth_configured else "mock_mode",
        message=oauth_msg,
        latency_ms=None,
    )

    # 5. Multimodal AI Provider
    ai_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    ai_health = ComponentHealth(
        status="healthy" if ai_configured else "heuristic_fallback",
        message=(
            "Google Gemini Multimodal API active (gemini-2.5-flash)"
            if ai_configured
            else "GEMINI_API_KEY unset: Heuristic rule-based segmentation engine active (visual frame AI disabled)"
        ),
        latency_ms=None,
    )

    # 6. Storage & Disk Capacity
    try:
        data_dir = os.path.abspath(settings.DATA_DIR)
        os.makedirs(data_dir, exist_ok=True)
        total, used, free = shutil.disk_usage(data_dir)
        free_gb = round(free / (1024**3), 2)
        is_disk_ok = free_gb > 1.0  # Require > 1 GB free space for video rendering
        storage_health = ComponentHealth(
            status="healthy" if is_disk_ok else "degraded",
            message=f"Storage path {data_dir}: {free_gb} GB free",
            latency_ms=None,
        )
    except Exception as exc:
        storage_health = ComponentHealth(
            status="degraded",
            message=f"Storage inspection error: {exc}",
            latency_ms=None,
        )

    # Compute overall readiness
    mode_str = "LOCAL IN-PROCESS" if settings.is_local_task_execution else "DISTRIBUTED CELERY"
    if settings.is_local_task_execution and not settings.is_production:
        critical_healthy = is_db_connected and storage_health.status == "healthy"
    else:
        critical_healthy = is_db_connected and redis_health.status == "healthy" and worker_health.status == "healthy"

    overall_status = "ready" if critical_healthy else "degraded"

    return ReadinessResponse(
        status=overall_status,
        execution_mode=mode_str,
        timestamp=datetime.now(timezone.utc),
        components={
            "database": db_health,
            "redis": redis_health,
            "celery_worker": worker_health,
            "youtube_oauth": oauth_health,
            "ai_provider": ai_health,
            "storage": storage_health,
        },
    )
