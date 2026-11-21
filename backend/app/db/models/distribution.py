"""Publishing Distribution & Scheduling Models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class YouTubeAccount(Base, TimestampMixin):
    """Connected YouTube Channel OAuth authorization details."""

    __tablename__ = "youtube_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_handle: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class PublishSchedule(Base, TimestampMixin):
    """Scheduled Shorts publication to authorized YouTube channel."""

    __tablename__ = "publish_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    render_job_id: Mapped[int] = mapped_column(ForeignKey("render_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_clips.id", ondelete="CASCADE"), index=True, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    slot_name: Mapped[str] = mapped_column(String(32), default="09:00", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    target_channel: Mapped[str] = mapped_column(String(128), default="Astro Rebel", nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    privacy_status: Mapped[str] = mapped_column(String(32), default="private", nullable=False)  # private | public | unlisted
    status: Mapped[str] = mapped_column(
        String(32), default="scheduled", index=True, nullable=False
    )  # scheduled | publishing | published | failed | cancelled
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    publish_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    upload_jobs: Mapped[list["UploadJob"]] = relationship("UploadJob", back_populates="schedule", cascade="all, delete-orphan", lazy="selectin")


class UploadJob(Base, TimestampMixin):
    """Execution telemetry for YouTube video upload attempts."""

    __tablename__ = "upload_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("publish_schedules.id", ondelete="CASCADE"), index=True, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="uploading", index=True, nullable=False
    )  # uploading | processing | verified | failed
    bytes_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    youtube_response_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    schedule: Mapped["PublishSchedule"] = relationship("PublishSchedule", back_populates="upload_jobs", lazy="selectin")
