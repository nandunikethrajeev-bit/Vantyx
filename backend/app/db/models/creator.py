"""Creator Registry Model & Channel Authorization Models."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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

    # OAuth Channel Authorization & Ownership Verification Fields
    oauth_status: Mapped[str] = mapped_column(
        String(32), default="disconnected", index=True, nullable=False
    )  # disconnected | pending | connected | expired | revoked
    google_account_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    google_account_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_channel_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    verified_channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Fernet encrypted
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Fernet encrypted
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    oauth_scopes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    sources: Mapped[List["VideoSource"]] = relationship(
        "VideoSource", back_populates="creator", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["CreatorAuditLog"]] = relationship(
        "CreatorAuditLog", back_populates="creator", cascade="all, delete-orphan"
    )
    asset_associations: Mapped[List["CreatorAssetAssociation"]] = relationship(
        "CreatorAssetAssociation", back_populates="creator", cascade="all, delete-orphan"
    )


class CreatorOAuthState(Base):
    """CSRF state parameter tracking for Google OAuth flows."""

    __tablename__ = "creator_oauth_states"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creators.id", ondelete="CASCADE"), index=True, nullable=False
    )
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class CreatorAuditLog(Base):
    """Immutable audit trail for creator authentication and ownership events."""

    __tablename__ = "creator_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creators.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )  # oauth_initiate | oauth_callback_success | oauth_callback_failure | token_refresh | channel_verified | channel_mismatch | oauth_revoked | oauth_disconnected | asset_associated
    channel_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    creator: Mapped["Creator"] = relationship("Creator", back_populates="audit_logs")


class CreatorAssetAssociation(Base):
    """Explicit mapping between a verified creator's master asset and a YouTube video."""

    __tablename__ = "creator_asset_associations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creators.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    asset_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    creator: Mapped["Creator"] = relationship("Creator", back_populates="asset_associations")

