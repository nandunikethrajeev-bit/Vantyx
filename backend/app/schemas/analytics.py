"""Pydantic schemas for Analytics, Intelligence & Feedback Loop."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChannelAnalyticsResponse(BaseModel):
    """Channel-level performance telemetry."""
    channel_id: str
    channel_name: str
    snapshot_date: str
    total_views: int
    total_subscribers: int
    subscribers_gained: int
    total_videos: int
    estimated_minutes_watched: float
    average_view_duration_seconds: float
    average_view_percentage: float
    collection_source: str
    is_delayed_reporting: bool

    class Config:
        from_attributes = True


class VideoAnalyticsSnapshotResponse(BaseModel):
    """Snapshot telemetry for a single published Short."""
    id: int
    schedule_id: Optional[int] = None
    youtube_video_id: str
    snapshot_date: str
    views: int
    likes: int
    comments: int
    shares: int
    subscribers_gained: int
    average_view_duration_seconds: float
    average_view_percentage: float
    estimated_minutes_watched: float
    retention_curve_data: Optional[List[Dict[str, Any]]] = None
    is_delayed_reporting: bool
    reporting_status: str
    collection_source: str

    class Config:
        from_attributes = True


class PublishedVideoPerformanceResponse(BaseModel):
    """Enriched performance view linking publish schedule and analytics."""
    schedule_id: int
    youtube_video_id: Optional[str] = None
    title: str
    slot_name: str
    scheduled_time: datetime
    age_days: int
    views: int
    likes: int
    comments: int
    shares: int
    subscribers_gained: int
    average_view_duration_seconds: float
    average_view_percentage: float
    relative_retention_index: float
    hook_retention_rate: float
    category: str
    duration_bucket: str
    reporting_status: str
    is_delayed_reporting: bool


class InsightBucket(BaseModel):
    """Comparative performance bucket with statistical confidence."""
    key: str
    label: str
    sample_size: int
    avg_views: float
    avg_retention_pct: float
    confidence_level: str  # low (N<3) | medium (3<=N<10) | high (N>=10)
    relative_multiplier: float
    rationale: str


class PerformanceIntelligenceResponse(BaseModel):
    """Statistical intelligence report across performance dimensions."""
    top_clips: List[Dict[str, Any]]
    hook_insights: List[InsightBucket]
    duration_insights: List[InsightBucket]
    category_insights: List[InsightBucket]
    slot_insights: List[InsightBucket]
    correlation_vs_causation_notice: str
    overall_confidence: str
    total_samples_analyzed: int


class AnalyticsCollectionJobResponse(BaseModel):
    """Audit record for analytics collection execution."""
    id: int
    job_id: str
    job_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    videos_probed: int
    snapshots_created: int
    errors_count: int
    error_details: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackStatusResponse(BaseModel):
    """Status of the closed-loop selection feedback engine."""
    feedback_enabled: bool
    max_impact: float
    min_sample_size: int
    category_multipliers: Dict[str, float]
    duration_multipliers: Dict[str, float]
    hook_multipliers: Dict[str, float]
    active_profiles_count: int


class FeedbackConfigUpdate(BaseModel):
    """Configuration patch for the feedback engine."""
    feedback_enabled: Optional[bool] = None
    max_impact: Optional[float] = Field(default=None, ge=0.0, le=0.30)
    min_sample_size: Optional[int] = Field(default=None, ge=1, le=50)
