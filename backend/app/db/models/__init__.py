"""VANTYX Database Models Package.

All domain models are registered and exported here.
"""

from app.db.base import Base
from app.db.models.creator import Creator
from app.db.models.source import VideoSource
from app.db.models.rights import RightsRecord
from app.db.models.intake import IntakeBatch, IntakeBatchItem
from app.db.models.intelligence import AnalysisJob, VideoScene
from app.db.models.selection import CandidateClip
from app.db.models.production import RenderJob
from app.db.models.distribution import PublishSchedule, UploadJob, YouTubeAccount
from app.db.models.orchestration import (
    WorkflowRun,
    WorkflowStep,
    BackgroundJob,
    JobAttempt,
    JobExecutionLog,
    DailyPublishingPlan,
)
from app.db.models.analytics import (
    ChannelAnalyticsSnapshot,
    VideoAnalyticsSnapshot,
    PerformanceMetrics,
    AnalyticsCollectionJob,
    ClipPerformanceProfile,
    VideoMetric,
)

__all__ = [
    "Base",
    "Creator",
    "VideoSource",
    "RightsRecord",
    "IntakeBatch",
    "IntakeBatchItem",
    "AnalysisJob",
    "VideoScene",
    "CandidateClip",
    "RenderJob",
    "PublishSchedule",
    "UploadJob",
    "YouTubeAccount",
    "WorkflowRun",
    "WorkflowStep",
    "BackgroundJob",
    "JobAttempt",
    "JobExecutionLog",
    "DailyPublishingPlan",
    "ChannelAnalyticsSnapshot",
    "VideoAnalyticsSnapshot",
    "PerformanceMetrics",
    "AnalyticsCollectionJob",
    "ClipPerformanceProfile",
    "VideoMetric",
]
