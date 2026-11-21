"""Video Production & Rendering Models."""

from typing import Optional
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class RenderJob(Base, TimestampMixin):
    """Video rendering task for 9:16 vertical short creation."""

    __tablename__ = "render_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_clips.id", ondelete="CASCADE"), index=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("video_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="queued", index=True, nullable=False
    )  # queued | rendering | completed | failed
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    output_file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    resolution: Mapped[str] = mapped_column(String(32), default="1080x1920", nullable=False)
    format_aspect: Mapped[str] = mapped_column(String(16), default="9:16", nullable=False)
    layout_style: Mapped[str] = mapped_column(String(64), default="blurred_backdrop", nullable=False)  # blurred_backdrop | crop_center
    has_burned_subtitles: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
