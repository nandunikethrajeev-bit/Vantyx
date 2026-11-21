"""Rights & Commercial Permission Management Model."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class RightsRecord(Base, TimestampMixin):
    """Legal rights, commercial authorizations, and editing scopes for media."""

    __tablename__ = "rights_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("video_sources.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    permission_status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )  # pending | authorized | rejected | revoked | own_gameplay
    commercial_use_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_editing_scope: Mapped[str] = mapped_column(
        String(64), default="transformative_shorts", nullable=False
    )  # full | clip_only | transformative_shorts | restricted
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attribution_text: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    license_documentation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped["VideoSource"] = relationship("VideoSource", back_populates="rights")
