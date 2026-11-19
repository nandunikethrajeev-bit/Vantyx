"""VANTYX Health Check Endpoints.

Provides /health for basic service liveness and /health/ready for
verifying dependency readiness (database connectivity, services).
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.db.session import check_db_connectivity
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
    return HealthResponse(
        status="ok",
        app=settings.PROJECT_NAME,
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Probes internal dependencies (such as PostgreSQL) to verify overall readiness.",
)
async def readiness_probe() -> ReadinessResponse:
    """Check readiness of dependencies."""
    start_time = time.perf_counter()
    is_db_connected, db_message = await check_db_connectivity()
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    db_health = ComponentHealth(
        status="healthy" if is_db_connected else "unreachable",
        message=db_message,
        latency_ms=latency_ms if is_db_connected else None,
    )

    overall_status = "ready" if is_db_connected else "degraded"

    return ReadinessResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        components={
            "database": db_health,
        },
    )
