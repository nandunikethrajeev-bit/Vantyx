"""VANTYX AI Intelligence Endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.intelligence.service import IntelligenceService
from app.schemas.intelligence import (
    AnalysisJobResponse,
    TriggerAnalysisRequest,
    VideoSceneResponse,
)

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence Engine"])


@router.post(
    "/analyze/{source_id}",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger AI Video Intelligence Analysis",
)
async def analyze_video_source(
    source_id: int,
    request: TriggerAnalysisRequest = TriggerAnalysisRequest(),
    db: AsyncSession = Depends(get_db),
) -> AnalysisJobResponse:
    try:
        job = await IntelligenceService.start_video_analysis(
            db=db,
            source_id=source_id,
            force=request.force_reanalysis,
            provider_name=request.provider_override,
        )
        resp = AnalysisJobResponse.model_validate(job)
        resp.scene_count = len(job.scenes) if job.scenes else 0
        resp.scenes = [
            VideoSceneResponse(
                id=s.id,
                job_id=s.job_id,
                source_id=s.source_id,
                start_time=s.start_time,
                end_time=s.end_time,
                duration_seconds=round(s.end_time - s.start_time, 1),
                scene_label=s.scene_label,
                description=s.description,
                speech_transcript=s.speech_transcript,
                action_intensity=s.action_intensity,
                excitement_score=s.excitement_score,
                tags=s.tags,
                created_at=s.created_at,
            )
            for s in (job.scenes or [])
        ]
        return resp
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {exc}")


@router.get(
    "/jobs",
    response_model=List[AnalysisJobResponse],
    summary="List Analysis Jobs",
)
async def list_jobs(
    source_id: Optional[int] = Query(None, description="Filter jobs by video source ID"),
    db: AsyncSession = Depends(get_db),
) -> List[AnalysisJobResponse]:
    jobs = await IntelligenceService.list_jobs(db, source_id=source_id)
    responses = []
    for j in jobs:
        resp = AnalysisJobResponse.model_validate(j)
        resp.scene_count = len(j.scenes) if j.scenes else 0
        responses.append(resp)
    return responses


@router.get(
    "/jobs/{job_id}",
    response_model=AnalysisJobResponse,
    summary="Get Analysis Job Details with Scenes",
)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalysisJobResponse:
    job = await IntelligenceService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    resp = AnalysisJobResponse.model_validate(job)
    resp.scene_count = len(job.scenes) if job.scenes else 0
    resp.scenes = [
        VideoSceneResponse(
            id=s.id,
            job_id=s.job_id,
            source_id=s.source_id,
            start_time=s.start_time,
            end_time=s.end_time,
            duration_seconds=round(s.end_time - s.start_time, 1),
            scene_label=s.scene_label,
            description=s.description,
            speech_transcript=s.speech_transcript,
            action_intensity=s.action_intensity,
            excitement_score=s.excitement_score,
            tags=s.tags,
            created_at=s.created_at,
        )
        for s in (job.scenes or [])
    ]
    return resp


@router.get(
    "/sources/{source_id}/scenes",
    response_model=List[VideoSceneResponse],
    summary="List Extracted Scenes for Video Source",
)
async def list_source_scenes(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> List[VideoSceneResponse]:
    scenes = await IntelligenceService.list_source_scenes(db, source_id)
    return [
        VideoSceneResponse(
            id=s.id,
            job_id=s.job_id,
            source_id=s.source_id,
            start_time=s.start_time,
            end_time=s.end_time,
            duration_seconds=round(s.end_time - s.start_time, 1),
            scene_label=s.scene_label,
            description=s.description,
            speech_transcript=s.speech_transcript,
            action_intensity=s.action_intensity,
            excitement_score=s.excitement_score,
            tags=s.tags,
            created_at=s.created_at,
        )
        for s in scenes
    ]
