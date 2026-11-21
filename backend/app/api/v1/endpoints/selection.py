"""VANTYX Intelligent Clip Selection Endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.selection.service import RankingWeights, SelectionService
from app.schemas.selection import (
    CandidateClipResponse,
    CandidateClipUpdate,
    DailySelectionResponse,
    GenerateCandidatesRequest,
)

router = APIRouter(prefix="/selection", tags=["Intelligent Clip Selection"])


@router.post(
    "/generate/{source_id}",
    response_model=List[CandidateClipResponse],
    status_code=status.HTTP_200_OK,
    summary="Rank & Generate Candidate Clips from Indexed Scenes",
)
async def generate_candidates(
    source_id: int,
    request: GenerateCandidatesRequest = GenerateCandidatesRequest(),
    db: AsyncSession = Depends(get_db),
) -> List[CandidateClipResponse]:
    clips = await SelectionService.generate_candidates_for_source(
        db=db,
        source_id=source_id,
        min_score_threshold=request.min_score_threshold,
        max_candidates=request.max_candidates,
        weights=RankingWeights.from_schema(request.weights),
    )
    return [CandidateClipResponse.model_validate(c) for c in clips]


@router.get(
    "/candidates",
    response_model=List[CandidateClipResponse],
    summary="List Ranked Candidate Clips",
)
async def list_candidates(
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    status: Optional[str] = Query(None, description="candidate | approved | rejected | produced"),
    db: AsyncSession = Depends(get_db),
) -> List[CandidateClipResponse]:
    clips = await SelectionService.list_candidates(db, source_id=source_id, status=status)
    return [CandidateClipResponse.model_validate(c) for c in clips]


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateClipResponse,
    summary="Get Candidate Clip Details",
)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
) -> CandidateClipResponse:
    clip = await SelectionService.get_candidate(db, candidate_id)
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate clip not found")
    return CandidateClipResponse.model_validate(clip)


@router.patch(
    "/candidates/{candidate_id}",
    response_model=CandidateClipResponse,
    summary="Update Candidate Clip Status, Title or Timestamps",
)
async def update_candidate(
    candidate_id: int,
    data: CandidateClipUpdate,
    db: AsyncSession = Depends(get_db),
) -> CandidateClipResponse:
    clip = await SelectionService.update_candidate(db, candidate_id, data)
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate clip not found")
    return CandidateClipResponse.model_validate(clip)


@router.get(
    "/daily-queue",
    response_model=DailySelectionResponse,
    summary="Get Top 4 Candidate Clips for Daily Shorts Pipeline",
)
async def get_daily_queue(
    target_count: int = Query(4, ge=1, le=8, description="Target daily Shorts count"),
    db: AsyncSession = Depends(get_db),
) -> DailySelectionResponse:
    clips, has_sufficient = await SelectionService.get_daily_selection(db, target_count=target_count)
    return DailySelectionResponse(
        target_count=target_count,
        selected_count=len(clips),
        has_sufficient_moments=has_sufficient,
        candidates=[CandidateClipResponse.model_validate(c) for c in clips],
    )
