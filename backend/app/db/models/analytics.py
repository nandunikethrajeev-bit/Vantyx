"""Channel Analytics & Feedback Loop Models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class VideoMetric(Base, TimestampMixin):
    """Post-publication telemetry metrics for YouTube Shorts."""

    __tablename__ = "video_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("publish_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    youtube_video_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_view_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retention_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
