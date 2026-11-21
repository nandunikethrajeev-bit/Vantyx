"""VANTYX AI Intelligence Schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VideoSceneResponse(BaseModel):
    id: int
    job_id: int
    source_id: int
    start_time: float
    end_time: float
    duration_seconds: float = 0.0
    scene_label: str
    description: Optional[str] = None
    speech_transcript: Optional[str] = None
    action_intensity: float
    excitement_score: float
    tags: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisJobResponse(BaseModel):
    id: int
    source_id: int
    video_title: Optional[str] = None
    status: str  # pending | processing | completed | failed
    provider: str
    error_message: Optional[str] = None
    scene_count: int = 0
    scenes: List[VideoSceneResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TriggerAnalysisRequest(BaseModel):
    force_reanalysis: bool = Field(default=False, description="Re-analyze even if cached result exists")
    provider_override: Optional[str] = Field(None, description="gemini | heuristic")
