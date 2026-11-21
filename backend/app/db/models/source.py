"""Discovered Video Source Catalog Model."""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class VideoSource(Base, TimestampMixin):
    """Raw long-form gameplay video discovered or ingested."""

    __tablename__ = "video_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True)
    video_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    discovery_method: Mapped[str] = mapped_column(String(64), default="feed_ingest", nullable=False)  # feed_ingest | youtube_api | manual_import
    local_video_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    raw_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    creator: Mapped[Optional["Creator"]] = relationship("Creator", back_populates="sources", lazy="selectin")
    rights: Mapped[Optional["RightsRecord"]] = relationship("RightsRecord", back_populates="source", uselist=False, cascade="all, delete-orphan", lazy="selectin")
