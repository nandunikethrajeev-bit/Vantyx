"""VANTYX Database Models Package.

All domain models are registered and exported here.
"""

from app.db.base import Base
from app.db.models.creator import Creator
from app.db.models.source import VideoSource
from app.db.models.rights import RightsRecord
from app.db.models.intelligence import AnalysisJob, VideoScene
from app.db.models.selection import CandidateClip
from app.db.models.production import RenderJob
from app.db.models.distribution import PublishSchedule, UploadJob, YouTubeAccount
from app.db.models.orchestration import PipelineRun, PipelineLog
from app.db.models.analytics import VideoMetric

__all__ = [
    "Base",
    "Creator",
    "VideoSource",
    "RightsRecord",
    "AnalysisJob",
    "VideoScene",
    "CandidateClip",
    "RenderJob",
    "PublishSchedule",
    "UploadJob",
    "YouTubeAccount",
    "PipelineRun",
    "PipelineLog",
    "VideoMetric",
]
