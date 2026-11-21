"""Autonomous Orchestration & Telemetry Models."""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class PipelineRun(Base, TimestampMixin):
    """Daily autonomous orchestrator pipeline execution record."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_date: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(
        String(32), default="running", index=True, nullable=False
    )  # running | completed | failed | partial
    videos_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    videos_eligible: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moments_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clips_rendered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shorts_scheduled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineLog(Base, TimestampMixin):
    """Execution step log within an autonomous pipeline run."""

    __tablename__ = "pipeline_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # discovery | intelligence | selection | production | distribution
    level: Mapped[str] = mapped_column(String(16), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
