"""Pydantic Schemas for VANTYX Orchestration & Autonomous Workflow."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkflowStepResponse(BaseModel):
    id: int
    step_name: str
    step_order: int
    status: str  # pending | running | completed | failed | skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class JobAttemptResponse(BaseModel):
    id: int
    attempt_number: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    error_traceback: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BackgroundJobResponse(BaseModel):
    id: int
    job_id: str
    workflow_run_id: Optional[int] = None
    job_type: str
    payload: Optional[Dict[str, Any]] = None
    status: str  # pending | queued | running | completed | failed | retrying | cancelled
    priority: int
    worker_id: Optional[str] = None
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    max_retries: int
    current_retry: int
    error_message: Optional[str] = None
    attempts: List[JobAttemptResponse] = []

    model_config = ConfigDict(from_attributes=True)


class JobExecutionLogResponse(BaseModel):
    id: int
    workflow_run_id: Optional[int] = None
    job_id: Optional[int] = None
    level: str
    message: str
    context_data: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunResponse(BaseModel):
    id: int
    run_id: str
    workflow_type: str
    target_date: str
    status: str  # pending | queued | running | completed | failed | retrying | cancelled | paused
    current_step: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None
    retry_count: int
    execution_metadata: Optional[Dict[str, Any]] = None
    steps: List[WorkflowStepResponse] = []
    logs: List[JobExecutionLogResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DailyPublishingPlanResponse(BaseModel):
    id: int
    plan_date: str
    timezone: str
    status: str  # planning | ready | in_progress | fulfilled | partial | unfulfilled
    target_count: int
    filled_count: int
    slot_assignments: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StartWorkflowRequest(BaseModel):
    target_date: Optional[str] = Field(None, description="Target publish date formatted as YYYY-MM-DD")
    force: bool = Field(False, description="Force start even if workflow for target date already exists")
    execute_sync: bool = Field(True, description="Execute pipeline steps synchronously in this request")


class AutomationStatusResponse(BaseModel):
    automation_enabled: bool
    daily_run_time_ist: str
    timezone: str
    celery_mode: str  # eager | distributed
    redis_connected: bool
    active_worker_count: int
    max_concurrent_renders: int
    current_workflow_id: Optional[str] = None
    today_plan_status: Optional[str] = None
    filled_slots_today: int = 0
    next_scheduled_run: Optional[str] = None
    disk_free_gb: float


class AutomationConfigUpdate(BaseModel):
    automation_enabled: Optional[bool] = None
    daily_run_time_ist: Optional[str] = None
    max_concurrent_renders: Optional[int] = None
