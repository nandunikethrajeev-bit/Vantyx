"""Clip Candidate Selection Models."""

from typing import Optional
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class CandidateClip(Base, TimestampMixin):
    """Selected candidate moment evaluated for vertical Shorts conversion."""

    __tablename__ = "candidate_clips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("video_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    scene_id: Mapped[Optional[int]] = mapped_column(ForeignKey("video_scenes.id", ondelete="SET NULL"), nullable=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    title_suggestion: Mapped[str] = mapped_column(String(255), nullable=False)
    hook_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)        # 0.0 - 100.0
    retention_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)   # 0.0 - 100.0
    context_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)     # 0.0 - 100.0
    audio_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)       # 0.0 - 100.0
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="candidate", index=True, nullable=False
    )  # candidate | approved | rejected | produced
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
