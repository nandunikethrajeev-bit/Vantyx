"""Intelligence Analysis & Scene Models."""

from typing import Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class AnalysisJob(Base, TimestampMixin):
    """AI analysis execution record for a video source."""

    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("video_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)  # pending | processing | completed | failed
    provider: Mapped[str] = mapped_column(String(64), default="gemini", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    scenes: Mapped[List["VideoScene"]] = relationship("VideoScene", back_populates="job", cascade="all, delete-orphan")


class VideoScene(Base, TimestampMixin):
    """Detected scene boundary and semantic segment."""

    __tablename__ = "video_scenes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("video_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    scene_label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    speech_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_intensity: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0.0 - 1.0
    excitement_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0.0 - 1.0
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    audio_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="scenes")
