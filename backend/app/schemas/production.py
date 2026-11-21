"""VANTYX Video Production & Rendering Schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RenderSettingsInput(BaseModel):
    """Configuration options for vertical video rendering."""
    layout_style: str = Field(
        default="blurred_backdrop",
        description="blurred_backdrop | crop_center",
    )
    has_burned_subtitles: bool = Field(
        default=True,
        description="Whether to render subtitle text overlay onto the vertical canvas",
    )
    resolution: str = Field(default="1080x1920", description="Target video resolution")
    normalize_audio: bool = Field(default=True, description="Apply EBU R128 loudness normalization")


class RenderJobBase(BaseModel):
    candidate_id: int
    source_id: int
    resolution: str = "1080x1920"
    format_aspect: str = "9:16"
    layout_style: str = "blurred_backdrop"
    has_burned_subtitles: bool = True


class RenderJobCreate(RenderJobBase):
    pass


class RenderJobResponse(RenderJobBase):
    id: int
    status: str  # queued | rendering | completed | failed
    progress_pct: float
    output_file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
