"""VANTYX Video Production & Rendering Endpoints."""

import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.modules.production.service import ProductionService
from app.schemas.production import RenderJobResponse, RenderSettingsInput

router = APIRouter(prefix="/production", tags=["Video Production"])


@router.post(
    "/render/{candidate_id}",
    response_model=RenderJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger 9:16 Vertical Short Rendering",
)
async def trigger_render(
    candidate_id: int,
    settings: RenderSettingsInput = RenderSettingsInput(),
    db: AsyncSession = Depends(get_db),
) -> RenderJobResponse:
    try:
        job = await ProductionService.execute_render(
            db=db,
            candidate_id=candidate_id,
            render_settings=settings,
        )
        return RenderJobResponse.model_validate(job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rendering pipeline failed: {exc}",
        )


@router.get(
    "/jobs",
    response_model=List[RenderJobResponse],
    summary="List Video Render Jobs",
)
async def list_render_jobs(
    status: Optional[str] = Query(None, description="queued | rendering | completed | failed"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[RenderJobResponse]:
    jobs = await ProductionService.list_jobs(db, status=status, limit=limit)
    return [RenderJobResponse.model_validate(j) for j in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=RenderJobResponse,
    summary="Get Render Job Details",
)
async def get_render_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> RenderJobResponse:
    job = await ProductionService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Render job not found")
    return RenderJobResponse.model_validate(job)


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream Rendered 9:16 Short Video File",
)
async def stream_render_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    job = await ProductionService.get_job(db, job_id)
    if not job or not job.output_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Render job or file not found")
    
    # Path traversal protection
    export_dir = Path(settings.EXPORT_DIR).resolve()
    data_dir = Path(settings.DATA_DIR).resolve()
    target_path = Path(job.output_file_path).resolve()
    if export_dir not in target_path.parents and data_dir not in target_path.parents and target_path != export_dir and target_path != data_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: path traversal detected")

    if not os.path.exists(job.output_file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered video file is missing on disk")

    return FileResponse(
        path=job.output_file_path,
        media_type="video/mp4",
        filename=os.path.basename(job.output_file_path),
    )


@router.get(
    "/jobs/{job_id}/thumbnail",
    summary="Stream Rendered Video Thumbnail",
)
async def stream_render_thumbnail(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    job = await ProductionService.get_job(db, job_id)
    if not job or not job.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")

    # Path traversal protection
    export_dir = Path(settings.EXPORT_DIR).resolve()
    data_dir = Path(settings.DATA_DIR).resolve()
    thumb_path = Path(job.thumbnail_path).resolve()
    if export_dir not in thumb_path.parents and data_dir not in thumb_path.parents and thumb_path != export_dir and thumb_path != data_dir:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: path traversal detected")

    if not os.path.exists(job.thumbnail_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail image is missing on disk")

    return FileResponse(
        path=job.thumbnail_path,
        media_type="image/jpeg",
        filename=os.path.basename(job.thumbnail_path),
    )
