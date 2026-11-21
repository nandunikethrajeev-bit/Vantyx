"""Channel Analytics, Performance Intelligence & Feedback Loop Models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class ChannelAnalyticsSnapshot(Base, TimestampMixin):
    """Periodic performance snapshot for connected YouTube channel."""

    __tablename__ = "channel_analytics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    channel_name: Mapped[str] = mapped_column(String(255), default="Astro Rebel", nullable=False)
    snapshot_date: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # YYYY-MM-DD
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_subscribers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_videos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_minutes_watched: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_view_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_view_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    collection_source: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)  # api | mock
    is_delayed_reporting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    snapshot_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


class VideoAnalyticsSnapshot(Base, TimestampMixin):
    """Time-series performance snapshot for an individual published Short."""

    __tablename__ = "video_analytics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("publish_schedules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    youtube_video_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    snapshot_date: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # YYYY-MM-DD
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_view_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_view_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    estimated_minutes_watched: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retention_curve_data: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    is_delayed_reporting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reporting_status: Mapped[str] = mapped_column(
        String(32), default="complete", nullable=False
    )  # complete | partial | delayed | inaccessible
    collection_source: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)  # api | mock
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


class PerformanceMetrics(Base, TimestampMixin):
    """Aggregated analytical benchmarks across rolling observation windows."""

    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    metric_scope: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # channel | category | duration
    window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_avp: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    top_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)  # low | medium | high
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


class AnalyticsCollectionJob(Base, TimestampMixin):
    """Audit record for a batch analytics collection sweep."""

    __tablename__ = "analytics_collection_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), default="scheduled", nullable=False)  # scheduled | manual
    status: Mapped[str] = mapped_column(
        String(32), default="running", index=True, nullable=False
    )  # running | completed | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    videos_probed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    snapshots_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collection_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


class ClipPerformanceProfile(Base, TimestampMixin):
    """Normalized performance profile linking a clip candidate to audience retention."""

    __tablename__ = "clip_performance_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_clips.id", ondelete="CASCADE"), index=True, nullable=False
    )
    schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("publish_schedules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    relative_retention_index: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)  # 0.0 - 100.0
    hook_retention_rate: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)       # 0.0 - 100.0
    views_per_exposure_day: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    content_category: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    duration_bucket: Mapped[str] = mapped_column(String(32), default="25-35s", nullable=False)
    publish_slot: Mapped[str] = mapped_column(String(32), default="09:00", nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0.0 - 1.0
    feedback_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # Bounded [0.85, 1.15]


class VideoMetric(Base, TimestampMixin):
    """Legacy Post-publication telemetry metrics for backward compatibility."""

    __tablename__ = "video_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("publish_schedules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    youtube_video_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_view_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retention_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
