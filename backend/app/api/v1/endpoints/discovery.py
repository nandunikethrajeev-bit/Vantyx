"""VANTYX Discovery & Rights Management Endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.discovery.service import DiscoveryService
from app.schemas.discovery import (
    CreatorCreate,
    CreatorResponse,
    CreatorUpdate,
    DiscoveryRunResult,
    EligibilityCheckResponse,
    RightsRecordResponse,
    RightsRecordUpdate,
    VideoSourceCreate,
    VideoSourceResponse,
)

router = APIRouter(prefix="/discovery", tags=["Discovery & Rights"])


# ---------------- Creator Endpoints ----------------

@router.post(
    "/creators",
    response_model=CreatorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register GTA Creator",
)
async def register_creator(
    data: CreatorCreate,
    db: AsyncSession = Depends(get_db),
) -> CreatorResponse:
    existing = await DiscoveryService.get_creator_by_channel_id(db, data.channel_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Channel ID '{data.channel_id}' is already registered as '{existing.name}'.",
        )
    creator = await DiscoveryService.create_creator(db, data)
    return CreatorResponse.model_validate(creator)


@router.get(
    "/creators",
    response_model=List[CreatorResponse],
    summary="List Registered Creators",
)
async def list_creators(
    monitored_only: bool = Query(False, description="Filter only monitored channels"),
    approved_only: bool = Query(False, description="Filter only approved channels"),
    db: AsyncSession = Depends(get_db),
) -> List[CreatorResponse]:
    creators = await DiscoveryService.list_creators(db, monitored_only=monitored_only, approved_only=approved_only)
    return [CreatorResponse.model_validate(c) for c in creators]


@router.get(
    "/creators/{creator_id}",
    response_model=CreatorResponse,
    summary="Get Creator Details",
)
async def get_creator(
    creator_id: int,
    db: AsyncSession = Depends(get_db),
) -> CreatorResponse:
    creator = await DiscoveryService.get_creator(db, creator_id)
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    return CreatorResponse.model_validate(creator)


@router.patch(
    "/creators/{creator_id}",
    response_model=CreatorResponse,
    summary="Update Creator Parameters",
)
async def update_creator(
    creator_id: int,
    data: CreatorUpdate,
    db: AsyncSession = Depends(get_db),
) -> CreatorResponse:
    creator = await DiscoveryService.update_creator(db, creator_id, data)
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    return CreatorResponse.model_validate(creator)


@router.delete(
    "/creators/{creator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Creator",
)
async def delete_creator(
    creator_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await DiscoveryService.delete_creator(db, creator_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")


@router.post(
    "/creators/{creator_id}/discover",
    response_model=List[VideoSourceResponse],
    summary="Discover Videos from Channel",
)
async def discover_channel_videos(
    creator_id: int,
    db: AsyncSession = Depends(get_db),
) -> List[VideoSourceResponse]:
    creator = await DiscoveryService.get_creator(db, creator_id)
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

    new_sources, _ = await DiscoveryService.discover_channel_videos(db, creator)
    responses = []
    for s in new_sources:
        is_eligible, _ = DiscoveryService.evaluate_eligibility(s)
        resp = VideoSourceResponse.model_validate(s)
        resp.is_eligible = is_eligible
        resp.creator_name = creator.name
        responses.append(resp)
    return responses


@router.post(
    "/run",
    response_model=DiscoveryRunResult,
    summary="Run Discovery Across All Active Channels",
)
async def run_discovery_cycle(
    db: AsyncSession = Depends(get_db),
) -> DiscoveryRunResult:
    result = await DiscoveryService.run_discovery_cycle(db)
    return DiscoveryRunResult(**result)


# ---------------- Video Source Endpoints ----------------

@router.get(
    "/sources",
    response_model=List[VideoSourceResponse],
    summary="List Discovered Video Sources",
)
async def list_sources(
    creator_id: Optional[int] = Query(None, description="Filter by creator ID"),
    eligible_only: bool = Query(False, description="Filter only pipeline-eligible videos"),
    db: AsyncSession = Depends(get_db),
) -> List[VideoSourceResponse]:
    sources = await DiscoveryService.list_sources(db, creator_id=creator_id, eligible_only=eligible_only)
    responses = []
    for s in sources:
        is_eligible, _ = DiscoveryService.evaluate_eligibility(s)
        resp = VideoSourceResponse.model_validate(s)
        resp.is_eligible = is_eligible
        if s.creator:
            resp.creator_name = s.creator.name
        responses.append(resp)
    return responses


@router.post(
    "/sources",
    response_model=VideoSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually Register / Import Video Source",
)
async def manual_import_source(
    data: VideoSourceCreate,
    db: AsyncSession = Depends(get_db),
) -> VideoSourceResponse:
    try:
        source = await DiscoveryService.ingest_manual_source(db, data)
        is_eligible, _ = DiscoveryService.evaluate_eligibility(source)
        resp = VideoSourceResponse.model_validate(source)
        resp.is_eligible = is_eligible
        return resp
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/sources/{source_id}",
    response_model=VideoSourceResponse,
    summary="Get Source Video Details",
)
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> VideoSourceResponse:
    source = await DiscoveryService.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video source not found")
    is_eligible, _ = DiscoveryService.evaluate_eligibility(source)
    resp = VideoSourceResponse.model_validate(source)
    resp.is_eligible = is_eligible
    if source.creator:
        resp.creator_name = source.creator.name
    return resp


@router.put(
    "/sources/{source_id}/rights",
    response_model=RightsRecordResponse,
    summary="Update Source Commercial Permissions & Scope",
)
async def update_source_rights(
    source_id: int,
    data: RightsRecordUpdate,
    db: AsyncSession = Depends(get_db),
) -> RightsRecordResponse:
    source = await DiscoveryService.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video source not found")
    rights = await DiscoveryService.update_source_rights(db, source_id, data)
    return RightsRecordResponse.model_validate(rights)


@router.get(
    "/sources/{source_id}/eligibility",
    response_model=EligibilityCheckResponse,
    summary="Check Pipeline Legal Eligibility Gate",
)
async def check_source_eligibility(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> EligibilityCheckResponse:
    try:
        is_eligible, reason, source = await DiscoveryService.check_source_eligibility(db, source_id)
        status_val = source.rights.permission_status if source.rights else "none"
        commercial = source.rights.commercial_use_allowed if source.rights else False
        return EligibilityCheckResponse(
            source_id=source.id,
            video_id=source.video_id,
            is_eligible=is_eligible,
            permission_status=status_val,
            commercial_use_allowed=commercial,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
