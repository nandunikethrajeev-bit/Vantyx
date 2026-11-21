"""VANTYX Orchestration & Autonomous Control API Endpoints."""

import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import is_redis_available
from app.core.config import settings
from app.db.session import get_db
from app.modules.distribution.service import TimezoneHelper
from app.modules.orchestration.service import OrchestrationService
from app.schemas.orchestration import (
    AutomationConfigUpdate,
    AutomationStatusResponse,
    DailyPublishingPlanResponse,
    StartWorkflowRequest,
    WorkflowRunResponse,
)

router = APIRouter()


@router.get("/status", response_model=AutomationStatusResponse)
async def get_automation_status(db: AsyncSession = Depends(get_db)):
    """Retrieve autonomous pipeline system health, Redis connection, and scheduler status."""
    current_wf = await OrchestrationService.get_current_workflow(db)
    today_str = datetime.now(TimezoneHelper.KOLKATA_TZ).strftime("%Y-%m-%d")
    plan = await OrchestrationService.get_or_create_daily_plan(db, today_str)

    # Calculate free disk space
    free_gb = 0.0
    try:
        total, used, free = shutil.disk_usage(settings.DATA_DIR)
        free_gb = round(free / (1024**3), 2)
    except Exception:
        pass

    return AutomationStatusResponse(
        automation_enabled=settings.ORCHESTRATION_ENABLED,
        daily_run_time_ist=settings.DAILY_PIPELINE_RUN_TIME,
        timezone=settings.TIMEZONE,
        celery_mode="distributed" if is_redis_available and not settings.CELERY_ALWAYS_EAGER else "eager",
        redis_connected=is_redis_available,
        active_worker_count=1 if is_redis_available else 0,
        max_concurrent_renders=settings.MAX_CONCURRENT_RENDERS,
        current_workflow_id=current_wf.run_id if current_wf else None,
        today_plan_status=plan.status,
        filled_slots_today=plan.filled_count,
        next_scheduled_run=f"{today_str} {settings.DAILY_PIPELINE_RUN_TIME} IST",
        disk_free_gb=free_gb,
    )


@router.patch("/config", response_model=AutomationStatusResponse)
async def update_automation_config(
    update_data: AutomationConfigUpdate, db: AsyncSession = Depends(get_db)
):
    """Update runtime automation configuration (e.g. enable/disable scheduler)."""
    if update_data.automation_enabled is not None:
        settings.ORCHESTRATION_ENABLED = update_data.automation_enabled
    if update_data.daily_run_time_ist is not None:
        settings.DAILY_PIPELINE_RUN_TIME = update_data.daily_run_time_ist
    if update_data.max_concurrent_renders is not None:
        settings.MAX_CONCURRENT_RENDERS = update_data.max_concurrent_renders

    return await get_automation_status(db)


@router.post("/start", response_model=WorkflowRunResponse, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    request: StartWorkflowRequest = StartWorkflowRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Initialize and trigger a daily autonomous publishing workflow run."""
    run = await OrchestrationService.create_workflow_run(
        db, target_date=request.target_date, force=request.force
    )

    if request.execute_sync:
        # Run all 7 stages directly in this request
        run = await OrchestrationService.run_full_pipeline(db, run.run_id)

    # Return full workflow run with steps
    detailed = await OrchestrationService.get_workflow_by_id(db, run.run_id)
    return detailed or run


@router.get("/workflows/current", response_model=Optional[WorkflowRunResponse])
async def get_current_workflow(db: AsyncSession = Depends(get_db)):
    """Retrieve active or most recently executed workflow run."""
    return await OrchestrationService.get_current_workflow(db)


@router.get("/workflows", response_model=List[WorkflowRunResponse])
async def list_workflows(
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List execution history of autonomous workflow runs."""
    return await OrchestrationService.list_workflows(db, limit=limit, status=status_filter)


@router.get("/workflows/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_by_id(run_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve detailed state of a specific workflow run including all steps and logs."""
    run = await OrchestrationService.get_workflow_by_id(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found",
        )
    return run


@router.post("/workflows/{run_id}/pause", response_model=WorkflowRunResponse)
async def pause_workflow(run_id: str, db: AsyncSession = Depends(get_db)):
    """Pause an in-flight workflow run."""
    try:
        run = await OrchestrationService.pause_workflow(db, run_id)
        detailed = await OrchestrationService.get_workflow_by_id(db, run.run_id)
        return detailed or run
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/workflows/{run_id}/resume", response_model=WorkflowRunResponse)
async def resume_workflow(run_id: str, db: AsyncSession = Depends(get_db)):
    """Resume a paused workflow run."""
    try:
        run = await OrchestrationService.resume_workflow(db, run_id)
        detailed = await OrchestrationService.get_workflow_by_id(db, run.run_id)
        return detailed or run
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/workflows/{run_id}/cancel", response_model=WorkflowRunResponse)
async def cancel_workflow(run_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel an active or paused workflow run."""
    try:
        run = await OrchestrationService.cancel_workflow(db, run_id)
        detailed = await OrchestrationService.get_workflow_by_id(db, run.run_id)
        return detailed or run
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/plan", response_model=DailyPublishingPlanResponse)
async def get_daily_publishing_plan(
    target_date: Optional[str] = Query(None, description="Plan date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the 4-slot daily publishing plan in Asia/Kolkata timezone."""
    if not target_date:
        target_date = datetime.now(TimezoneHelper.KOLKATA_TZ).strftime("%Y-%m-%d")
    return await OrchestrationService.get_or_create_daily_plan(db, target_date)


@router.post("/recover", response_model=Dict[str, Any])
async def recover_stalled_workflows(db: AsyncSession = Depends(get_db)):
    """Detect and recover workflows stuck in 'running' state after application restart."""
    recovered = await OrchestrationService.recover_stalled_workflows(db)
    return {
        "recovered_count": recovered,
        "message": f"Successfully recovered {recovered} stalled workflow(s)",
    }
