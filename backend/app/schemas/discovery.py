"""VANTYX Discovery & Rights Management Schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------- Creator Schemas ----------------

class CreatorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Creator or channel name")
    channel_id: str = Field(..., min_length=1, max_length=128, description="Unique YouTube Channel ID (e.g. UC...)")
    channel_handle: Optional[str] = Field(None, max_length=128, description="YouTube @handle if known")
    channel_url: Optional[str] = Field(None, max_length=512, description="Full channel URL")
    content_category: str = Field(default="GTA 6 Gameplay", max_length=128)
    is_monitored: bool = Field(default=True)
    approval_status: str = Field(default="pending", description="pending | approved | rejected")
    permission_tier: str = Field(
        default="unverified",
        description="own_content | authorized_partner | public_creative_commons | unverified",
    )
    notes: Optional[str] = Field(None, description="Internal licensing notes")


class CreatorCreate(CreatorBase):
    pass


class CreatorUpdate(BaseModel):
    name: Optional[str] = None
    channel_handle: Optional[str] = None
    channel_url: Optional[str] = None
    content_category: Optional[str] = None
    is_monitored: Optional[bool] = None
    approval_status: Optional[str] = None
    permission_tier: Optional[str] = None
    notes: Optional[str] = None


class CreatorResponse(CreatorBase):
    id: int
    oauth_status: str = "disconnected"
    google_account_email: Optional[str] = None
    verified_channel_id: Optional[str] = None
    verified_channel_title: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Creator OAuth & Ownership Schemas ----------------

class CreatorOAuthInitiateResponse(BaseModel):
    configured: bool
    authorization_url: Optional[str] = None
    state: Optional[str] = None
    message: str
    mock_available: bool = False


class CreatorOAuthCallbackRequest(BaseModel):
    code: str
    state: str


class CreatorOAuthStatusResponse(BaseModel):
    creator_id: int
    creator_name: str
    channel_id: str
    oauth_status: str
    google_account_email: Optional[str] = None
    verified_channel_id: Optional[str] = None
    verified_channel_title: Optional[str] = None
    is_ownership_verified: bool = False
    is_revoked: bool = False
    token_expires_at: Optional[datetime] = None
    is_token_expired: bool = False
    verified_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    message: str


class CreatorAuditLogResponse(BaseModel):
    id: int
    creator_id: int
    event_type: str
    channel_id: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorAssetAssociationCreate(BaseModel):
    video_id: str = Field(..., min_length=11, max_length=128, description="YouTube Video ID")
    asset_filename: str = Field(..., min_length=1, max_length=255, description="Filename of master video in vault")
    notes: Optional[str] = Field(None, description="Optional association metadata")


class CreatorAssetAssociationResponse(BaseModel):
    id: int
    creator_id: int
    video_id: str
    asset_filename: str
    asset_path: str
    file_size_bytes: int
    duration_seconds: float
    is_verified: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorVaultStatusResponse(BaseModel):
    creator_id: int
    vault_directory: str
    total_files: int
    total_size_bytes: int
    files: List[Dict[str, Any]]
    associations: List[CreatorAssetAssociationResponse]


# ---------------- Rights Record Schemas ----------------

class RightsRecordBase(BaseModel):
    permission_status: str = Field(
        default="pending",
        description="pending | authorized | rejected | revoked | own_gameplay",
    )
    commercial_use_allowed: bool = Field(default=False)
    allowed_editing_scope: str = Field(
        default="transformative_shorts",
        description="full | clip_only | transformative_shorts | restricted",
    )
    attribution_required: bool = Field(default=True)
    attribution_text: Optional[str] = Field(None, max_length=512)
    license_documentation: Optional[str] = Field(None)
    verified_by: Optional[str] = Field(None, max_length=128)
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class RightsRecordUpdate(BaseModel):
    permission_status: Optional[str] = None
    commercial_use_allowed: Optional[bool] = None
    allowed_editing_scope: Optional[str] = None
    attribution_required: Optional[bool] = None
    attribution_text: Optional[str] = None
    license_documentation: Optional[str] = None
    verified_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class RightsRecordResponse(RightsRecordBase):
    id: int
    source_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Video Source Schemas ----------------

class VideoSourceBase(BaseModel):
    video_id: str = Field(..., max_length=128, description="YouTube Video ID or custom identifier")
    title: str = Field(..., max_length=512)
    description: Optional[str] = None
    duration_seconds: int = Field(default=0, ge=0)
    published_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    source_url: str = Field(..., max_length=1024)
    discovery_method: str = Field(default="manual_import")
    local_video_path: Optional[str] = None
    is_synthetic: bool = False
    raw_metadata: Optional[Dict[str, Any]] = None


class VideoSourceCreate(VideoSourceBase):
    creator_id: Optional[int] = None
    is_own_gameplay: bool = Field(default=False, description="Set true if this is own recorded gameplay")
    attribution_text: Optional[str] = None


class VideoSourceResponse(VideoSourceBase):
    id: int
    creator_id: Optional[int]
    creator_name: Optional[str] = None
    local_video_path: Optional[str] = None
    media_status: str = Field(default="awaiting_media", description="ready | awaiting_media | missing")
    rights: Optional[RightsRecordResponse] = None
    is_eligible: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkLocalMediaInput(BaseModel):
    local_path: str = Field(..., min_length=1, max_length=1024, description="Local path to authorized media file")


# ---------------- Operation Results ----------------

class EligibilityCheckResponse(BaseModel):
    source_id: int
    video_id: str
    is_eligible: bool
    permission_status: str
    commercial_use_allowed: bool
    reason: str


class DiscoveryRunResult(BaseModel):
    channels_polled: int
    videos_discovered: int
    duplicates_skipped: int
    errors: List[str]
    timestamp: datetime


# ---------------- Batch Intake Schemas ----------------

class BatchIntakeRequest(BaseModel):
    urls: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of 1 to 20 YouTube URLs to normalize, validate, and intake",
    )
    creator_id: Optional[int] = Field(
        default=None,
        description="Optional registered creator ID for commercial rights linkage",
    )
    is_own_gameplay: bool = Field(
        default=False,
        description="Caller claim of own gameplay (verified against creator record)",
    )
    notes: Optional[str] = Field(default=None, max_length=500)


class BatchItemResponse(BaseModel):
    id: int
    raw_url: str
    canonical_url: Optional[str] = None
    video_id: Optional[str] = None
    source_id: Optional[int] = None
    source_title: Optional[str] = None
    creator_name: Optional[str] = None
    source_category: Optional[str] = None
    source_provider: Optional[str] = None
    media_status: Optional[str] = None
    status: str
    is_eligible: bool = False
    permission_status: str = "pending"
    commercial_use_allowed: bool = False
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchIntakeResponse(BaseModel):
    batch_id: str
    creator_id: Optional[int] = None
    creator_name: Optional[str] = None
    total_submitted: int
    total_valid: int
    total_duplicates: int
    total_rejected: int
    status: str
    items: List[BatchItemResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

