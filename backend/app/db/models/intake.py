"""VANTYX Batch Intake & URL Tracking Models."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class IntakeBatch(Base, TimestampMixin):
    """Batch intake record representing a multi-URL submission by an operator."""

    __tablename__ = "intake_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    creator_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True
    )
    total_submitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_valid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="received", index=True, nullable=False
    )  # received | validating | completed | partially_completed | failed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    creator: Mapped[Optional["Creator"]] = relationship("Creator", lazy="selectin")
    items: Mapped[List["IntakeBatchItem"]] = relationship(
        "IntakeBatchItem", back_populates="batch", cascade="all, delete-orphan", lazy="selectin"
    )


class IntakeBatchItem(Base, TimestampMixin):
    """Individual URL entry within an intake batch."""

    __tablename__ = "intake_batch_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("intake_batches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("video_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="received", index=True, nullable=False
    )  # received | validating | pending_verification | eligible | rejected | duplicate | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    batch: Mapped["IntakeBatch"] = relationship("IntakeBatch", back_populates="items")
    source: Mapped[Optional["VideoSource"]] = relationship("VideoSource", lazy="selectin")
