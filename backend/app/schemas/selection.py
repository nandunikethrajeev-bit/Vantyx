"""VANTYX Clip Candidate Selection Schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RankingWeightsSchema(BaseModel):
    hook_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    retention_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    context_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    audio_weight: float = Field(default=0.15, ge=0.0, le=1.0)


class CandidateClipBase(BaseModel):
    source_id: int
    scene_id: Optional[int] = None
    start_time: float
    end_time: float
    duration_seconds: float
    title_suggestion: str
    hook_score: float = Field(ge=0.0, le=100.0)
    retention_score: float = Field(ge=0.0, le=100.0)
    context_score: float = Field(default=0.0, ge=0.0, le=100.0)
    audio_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)
    status: str = Field(default="candidate")  # candidate | approved | rejected | produced
    rationale: Optional[str] = None


class CandidateClipUpdate(BaseModel):
    status: Optional[str] = None  # candidate | approved | rejected | produced
    title_suggestion: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class CandidateClipResponse(CandidateClipBase):
    id: int
    video_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateCandidatesRequest(BaseModel):
    min_score_threshold: float = Field(default=60.0, ge=0.0, le=100.0)
    max_candidates: int = Field(default=8, ge=1, le=16)
    weights: Optional[RankingWeightsSchema] = None


class DailySelectionResponse(BaseModel):
    target_count: int = 4
    selected_count: int
    has_sufficient_moments: bool
    candidates: List[CandidateClipResponse]
