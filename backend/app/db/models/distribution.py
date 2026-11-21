"""Publishing Distribution & Scheduling Models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class PublishSchedule(Base, TimestampMixin):
    """Scheduled Shorts publication to authorized YouTube channel."""

    __tablename__ = "publish_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    render_job_id: Mapped[int] = mapped_column(ForeignKey("render_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_clips.id", ondelete="CASCADE"), index=True, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    target_channel: Mapped[str] = mapped_column(String(128), default="Astro Rebel", nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="scheduled", index=True, nullable=False
    )  # scheduled | publishing | published | failed | cancelled
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    publish_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
