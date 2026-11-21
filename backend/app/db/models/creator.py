"""Creator Registry Model."""

from typing import List, Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Creator(Base, TimestampMixin):
    """Registered video creator / content partner."""

    __tablename__ = "creators"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    channel_handle: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    channel_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    content_category: Mapped[str] = mapped_column(String(128), default="GTA 6 Gameplay", nullable=False)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    approval_status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )  # pending | approved | rejected
    permission_tier: Mapped[str] = mapped_column(
        String(64), default="unverified", nullable=False
    )  # own_content | authorized_partner | public_creative_commons | unverified
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sources: Mapped[List["VideoSource"]] = relationship("VideoSource", back_populates="creator", cascade="all, delete-orphan")
