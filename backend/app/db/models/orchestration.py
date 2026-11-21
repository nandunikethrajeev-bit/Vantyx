"""Orchestration & Autonomous Execution Pipeline Database Models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class WorkflowRun(Base, TimestampMixin):
    """Execution lifecycle of an autonomous end-to-end publishing pipeline."""

    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    workflow_type: Mapped[str] = mapped_column(
        String(64), default="daily_autonomous_publishing", nullable=False
    )
    target_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )  # pending | queued | running | completed | failed | retrying | cancelled | paused
    current_step: Mapped[str] = mapped_column(
        String(64), default="discovery", nullable=False
    )  # discovery | rights_validation | intelligence | selection | production | distribution | monitoring | completed
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    steps: Mapped[List["WorkflowStep"]] = relationship(
        "WorkflowStep",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
        lazy="selectin",
    )
    jobs: Mapped[List["BackgroundJob"]] = relationship(
        "BackgroundJob",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    logs: Mapped[List["JobExecutionLog"]] = relationship(
        "JobExecutionLog",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="JobExecutionLog.id",
        lazy="selectin",
    )


class WorkflowStep(Base, TimestampMixin):
    """Individual stage within a workflow run (Steps 1 through 7)."""

    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_run_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_name: Mapped[str] = mapped_column(String(64), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )  # pending | running | completed | failed | skipped
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    workflow_run: Mapped["WorkflowRun"] = relationship("WorkflowRun", back_populates="steps")


class BackgroundJob(Base, TimestampMixin):
    """Asynchronous background unit of work coordinated via Celery and Redis."""

    __tablename__ = "background_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    workflow_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )  # pending | queued | running | completed | failed | retrying | cancelled
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worker_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    current_retry: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workflow_run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun", back_populates="jobs")
    attempts: Mapped[List["JobAttempt"]] = relationship(
        "JobAttempt",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobAttempt.attempt_number",
        lazy="selectin",
    )


class JobAttempt(Base, TimestampMixin):
    """Historical execution record of an individual job execution or retry."""

    __tablename__ = "job_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("background_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # running | completed | failed
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["BackgroundJob"] = relationship("BackgroundJob", back_populates="attempts")


class JobExecutionLog(Base, TimestampMixin):
    """Structured operational and debugging log associated with a workflow or job."""

    __tablename__ = "job_execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("background_jobs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    level: Mapped[str] = mapped_column(String(16), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    workflow_run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun", back_populates="logs")


class DailyPublishingPlan(Base, TimestampMixin):
    """Persistent daily plan tracking 4 daily Shorts slot allocation in Asia/Kolkata."""

    __tablename__ = "daily_publishing_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_date: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="planning", index=True, nullable=False
    )  # planning | ready | in_progress | fulfilled | partial | unfulfilled
    target_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    filled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    slot_assignments: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
