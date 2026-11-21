"""VANTYX Distribution & YouTube Publishing Schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OAuthUrlResponse(BaseModel):
    configured: bool
    auth_url: Optional[str] = None
    message: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class YouTubeAccountResponse(BaseModel):
    id: int
    channel_id: str
    channel_title: str
    channel_handle: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool
    connected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublishScheduleBase(BaseModel):
    candidate_id: int
    render_job_id: int
    scheduled_time: datetime
    slot_name: str = "09:00"
    timezone: str = "Asia/Kolkata"
    target_channel: str = "Astro Rebel"
    title: str = Field(..., max_length=100)
    description: Optional[str] = None
    tags: Optional[str] = None
    privacy_status: str = "private"


class PublishScheduleCreate(BaseModel):
    candidate_id: int
    render_job_id: int
    target_date: str = Field(..., description="Target publish date formatted as YYYY-MM-DD")
    slot_name: str = Field(..., description="One of: 09:00, 13:00, 17:00, 21:00")
    title: Optional[str] = Field(None, max_length=100)
    custom_description: Optional[str] = None


class PublishScheduleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    slot_name: Optional[str] = None
    status: Optional[str] = None


class UploadJobResponse(BaseModel):
    id: int
    schedule_id: int
    attempt_number: int
    status: str  # uploading | processing | verified | failed
    bytes_uploaded: int
    total_bytes: int
    error_detail: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PublishScheduleResponse(PublishScheduleBase):
    id: int
    status: str  # scheduled | publishing | published | failed | cancelled
    youtube_video_id: Optional[str] = None
    publish_url: Optional[str] = None
    retry_count: int = 0
    is_mock: bool = False
    error_message: Optional[str] = None
    upload_jobs: List[UploadJobResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlotInfo(BaseModel):
    slot_name: str
    scheduled_time_utc: datetime
    scheduled_time_local: str
    status: str  # unfilled | scheduled | published | expired
    schedule: Optional[PublishScheduleResponse] = None


class DailySlotsResponse(BaseModel):
    target_date: str
    timezone: str = "Asia/Kolkata"
    slots: List[SlotInfo]


class PublishTriggerResponse(BaseModel):
    schedule_id: int
    status: str
    youtube_video_id: Optional[str] = None
    publish_url: Optional[str] = None
    is_mock: bool = False
    message: str
