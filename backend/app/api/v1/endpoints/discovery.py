"""VANTYX Discovery & Rights Management Endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.discovery.service import DiscoveryService
from app.schemas.discovery import (
    BatchIntakeRequest,
    BatchIntakeResponse,
    BatchItemResponse,
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

def _format_batch_response(batch) -> BatchIntakeResponse:
    item_responses = []
    for it in (batch.items or []):
        is_elig = False
        perm_status = "none"
        comm_allowed = False
        if it.source and it.source.rights:
            perm_status = it.source.rights.permission_status
            comm_allowed = it.source.rights.commercial_use_allowed
            is_elig, _ = DiscoveryService.evaluate_eligibility(it.source)
        item_responses.append(
            BatchItemResponse(
                id=it.id,
                raw_url=it.raw_url,
                canonical_url=it.canonical_url,
                video_id=it.video_id,
                source_id=it.source_id,
                status=it.status,
                is_eligible=is_elig,
                permission_status=perm_status,
                commercial_use_allowed=comm_allowed,
                error_message=it.error_message,
                created_at=it.created_at,
            )
        )
    return BatchIntakeResponse(
        batch_id=batch.batch_id,
        creator_id=batch.creator_id,
        creator_name=batch.creator.name if batch.creator else None,
        total_submitted=batch.total_submitted,
        total_valid=batch.total_valid,
        total_duplicates=batch.total_duplicates,
        total_rejected=batch.total_rejected,
        status=batch.status,
        items=item_responses,
        created_at=batch.created_at,
    )


@router.post(
    "/sources/batch",
    response_model=BatchIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch Ingest and Normalize YouTube URLs",
)
async def batch_ingest_sources(
    data: BatchIntakeRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchIntakeResponse:
    if not data.urls or len(data.urls) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Batch must contain between 1 and 20 URLs. None received.",
        )
    if len(data.urls) > 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch exceeds maximum limit of 20 URLs. Received {len(data.urls)}.",
        )
    try:
        batch = await DiscoveryService.ingest_batch(db, data)
        full_batch = await DiscoveryService.get_batch(db, batch.batch_id)
        return _format_batch_response(full_batch or batch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/batches/{batch_id}",
    response_model=BatchIntakeResponse,
    summary="Get Intake Batch Details & Items",
)
async def get_batch_details(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
) -> BatchIntakeResponse:
    batch = await DiscoveryService.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found.")
    return _format_batch_response(batch)


@router.get(
    "/batches",
    response_model=List[BatchIntakeResponse],
    summary="List Recent Intake Batches",
)
async def list_intake_batches(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[BatchIntakeResponse]:
    batches = await DiscoveryService.list_batches(db, limit=limit)
    return [_format_batch_response(b) for b in batches]

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
