"""VANTYX Discovery & Rights Management Endpoints."""

import os
import time
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models.intake import IntakeBatchItem
from app.db.session import get_db
from app.modules.discovery.service import DiscoveryService
from app.modules.discovery.creator_oauth_service import CreatorOAuthService
from app.modules.discovery.creator_asset_service import CreatorAssetService
from app.schemas.discovery import (
    BatchIntakeRequest,
    BatchIntakeResponse,
    BatchItemResponse,
    CreatorAssetAssociationCreate,
    CreatorAssetAssociationResponse,
    CreatorAuditLogResponse,
    CreatorCreate,
    CreatorOAuthCallbackRequest,
    CreatorOAuthInitiateResponse,
    CreatorOAuthStatusResponse,
    CreatorResponse,
    CreatorUpdate,
    CreatorVaultStatusResponse,
    DiscoveryRunResult,
    EligibilityCheckResponse,
    LinkLocalMediaInput,
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


# ---------------- Creator OAuth & Channel Authorization ----------------

@router.get(
    "/creators/{creator_id}/oauth/authorize",
    response_model=CreatorOAuthInitiateResponse,
    summary="Initiate Google OAuth Flow for Creator",
)
@router.post(
    "/creators/{creator_id}/oauth/authorize",
    response_model=CreatorOAuthInitiateResponse,
    summary="Initiate Google OAuth Flow for Creator",
)
async def initiate_creator_oauth(
    creator_id: int,
    request: Request,
    redirect_uri: Optional[str] = Query(None, description="Custom OAuth redirect URI"),
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthInitiateResponse:
    client_ip = request.client.host if request.client else None
    return await CreatorOAuthService.initiate_oauth(
        db, creator_id=creator_id, redirect_uri_override=redirect_uri, ip_address=client_ip
    )


@router.post(
    "/creators/{creator_id}/oauth/callback",
    response_model=CreatorOAuthStatusResponse,
    summary="Handle Google OAuth Callback for Creator",
)
async def handle_creator_oauth_callback(
    creator_id: int,
    data: CreatorOAuthCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthStatusResponse:
    client_ip = request.client.host if request.client else None
    return await CreatorOAuthService.handle_oauth_callback(
        db, code=data.code, state=data.state, ip_address=client_ip
    )


@router.get(
    "/creators/oauth/callback",
    summary="Handle Direct Browser Redirect from Google OAuth",
)
async def handle_direct_oauth_callback(
    code: str = Query(..., description="Google authorization code"),
    state: str = Query(..., description="CSRF state parameter"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthStatusResponse:
    client_ip = request.client.host if request and request.client else None
    return await CreatorOAuthService.handle_oauth_callback(
        db, code=code, state=state, ip_address=client_ip
    )


@router.get(
    "/creators/{creator_id}/oauth/status",
    response_model=CreatorOAuthStatusResponse,
    summary="Get Creator OAuth & Channel Verification Status",
)
async def get_creator_oauth_status(
    creator_id: int,
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthStatusResponse:
    return await CreatorOAuthService.get_oauth_status(db, creator_id=creator_id)


@router.post(
    "/creators/{creator_id}/oauth/refresh",
    response_model=CreatorOAuthStatusResponse,
    summary="Refresh Creator Google OAuth Token",
)
async def refresh_creator_token(
    creator_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthStatusResponse:
    client_ip = request.client.host if request.client else None
    return await CreatorOAuthService.refresh_access_token(db, creator_id=creator_id, ip_address=client_ip)


@router.post(
    "/creators/{creator_id}/oauth/revoke",
    response_model=CreatorOAuthStatusResponse,
    summary="Revoke Creator Channel Authorization",
)
async def revoke_creator_oauth(
    creator_id: int,
    request: Request,
    reason: str = Query("Revoked by channel owner", description="Revocation rationale"),
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthStatusResponse:
    client_ip = request.client.host if request.client else None
    return await CreatorOAuthService.revoke_authorization(
        db, creator_id=creator_id, reason=reason, ip_address=client_ip
    )


@router.post(
    "/creators/{creator_id}/oauth/disconnect",
    response_model=CreatorOAuthStatusResponse,
    summary="Disconnect Creator Channel",
)
async def disconnect_creator_channel(
    creator_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CreatorOAuthStatusResponse:
    client_ip = request.client.host if request.client else None
    return await CreatorOAuthService.disconnect_channel(db, creator_id=creator_id, ip_address=client_ip)


@router.get(
    "/creators/{creator_id}/audit-logs",
    response_model=List[CreatorAuditLogResponse],
    summary="List Creator Security & Ownership Audit Events",
)
async def list_creator_audit_logs(
    creator_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[CreatorAuditLogResponse]:
    return await CreatorOAuthService.list_audit_logs(db, creator_id=creator_id, limit=limit)


# ---------------- Creator Vault & Master Asset Association ----------------

@router.get(
    "/creators/{creator_id}/vault/status",
    response_model=CreatorVaultStatusResponse,
    summary="Inspect Creator Vault Files and Mappings",
)
async def get_creator_vault_status(
    creator_id: int,
    db: AsyncSession = Depends(get_db),
) -> CreatorVaultStatusResponse:
    return await CreatorAssetService.get_vault_status(db, creator_id=creator_id)


@router.post(
    "/creators/{creator_id}/assets/associate",
    response_model=CreatorAssetAssociationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Associate Master Vault Asset with YouTube Video ID",
)
async def associate_creator_asset(
    creator_id: int,
    data: CreatorAssetAssociationCreate,
    db: AsyncSession = Depends(get_db),
) -> CreatorAssetAssociationResponse:
    return await CreatorAssetService.associate_asset(db, creator_id=creator_id, data=data)


@router.delete(
    "/creators/{creator_id}/assets/{association_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Master Video Association",
)
async def delete_creator_asset_association(
    creator_id: int,
    association_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    await CreatorAssetService.delete_association(db, creator_id=creator_id, association_id=association_id)


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
        source_title = None
        creator_name = None
        source_category = "unresolved"
        source_provider = None
        media_status = "awaiting_authorized_media"

        if it.source:
            source_title = it.source.title
            if it.source.creator:
                creator_name = it.source.creator.name
            if it.source.local_video_path:
                p = Path(it.source.local_video_path)
                if p.exists() and p.is_file() and p.stat().st_size > 1024:
                    media_status = "media_ready"

            if it.source.rights:
                perm_status = it.source.rights.permission_status
                comm_allowed = it.source.rights.commercial_use_allowed
                is_elig, _ = DiscoveryService.evaluate_eligibility(it.source)

            from app.modules.media_resolution.rights_evaluator import RightsEvaluator
            auth_eval = RightsEvaluator.evaluate(it.source)
            source_category = auth_eval.category.value

        item_responses.append(
            BatchItemResponse(
                id=it.id,
                raw_url=it.raw_url,
                canonical_url=it.canonical_url,
                video_id=it.video_id,
                source_id=it.source_id,
                source_title=source_title,
                creator_name=creator_name,
                source_category=source_category,
                source_provider=source_provider,
                media_status=media_status,
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
    summary="Batch Ingest, Normalize, and Process YouTube URLs",
)
async def batch_ingest_sources(
    data: BatchIntakeRequest,
    auto_process: bool = Query(False, description="Immediately trigger autonomous pipeline execution"),
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
        if auto_process:
            from app.modules.orchestration.pipeline_engine import AutonomousPipelineService
            await AutonomousPipelineService.process_batch(db, batch.batch_id, auto_render_top=True)

        full_batch = await DiscoveryService.get_batch(db, batch.batch_id)
        return _format_batch_response(full_batch or batch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/batches/{batch_id}/process",
    response_model=BatchIntakeResponse,
    summary="Trigger Autonomous Pipeline on Existing Batch",
)
async def process_intake_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
) -> BatchIntakeResponse:
    batch = await DiscoveryService.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found.")
    from app.modules.orchestration.pipeline_engine import AutonomousPipelineService
    await AutonomousPipelineService.process_batch(db, batch_id, auto_render_top=True)
    full_batch = await DiscoveryService.get_batch(db, batch_id)
    return _format_batch_response(full_batch or batch)


@router.post(
    "/batches/items/{item_id}/retry",
    response_model=BatchItemResponse,
    summary="Retry Autonomous Pipeline on Batch Item",
)
async def retry_batch_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> BatchItemResponse:
    from app.modules.orchestration.pipeline_engine import AutonomousPipelineService
    await AutonomousPipelineService.process_item(db, item_id, auto_render_top=True)

    stmt = (
        select(IntakeBatchItem)
        .where(IntakeBatchItem.id == item_id)
        .options(
            selectinload(IntakeBatchItem.source).selectinload(VideoSource.rights),
        )
    )
    item = (await db.execute(stmt)).scalars().first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch item not found")

    is_elig = False
    perm_status = "none"
    comm_allowed = False
    if item.source and item.source.rights:
        perm_status = item.source.rights.permission_status
        comm_allowed = item.source.rights.commercial_use_allowed
        is_elig, _ = DiscoveryService.evaluate_eligibility(item.source)

    return BatchItemResponse(
        id=item.id,
        raw_url=item.raw_url,
        canonical_url=item.canonical_url,
        video_id=item.video_id,
        source_id=item.source_id,
        status=item.status,
        is_eligible=is_elig,
        permission_status=perm_status,
        commercial_use_allowed=comm_allowed,
        error_message=item.error_message,
        created_at=item.created_at,
    )


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

def _build_source_response(s) -> VideoSourceResponse:
    """Build unified VideoSourceResponse with accurate media_status and rights."""
    is_eligible, _ = DiscoveryService.evaluate_eligibility(s)
    media_status = "awaiting_media"
    if s.local_video_path:
        p = Path(s.local_video_path)
        if not p.is_absolute():
            p = Path(os.getcwd()) / p
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            media_status = "ready"
        else:
            media_status = "missing"

    resp = VideoSourceResponse.model_validate(s)
    resp.is_eligible = is_eligible
    resp.media_status = media_status
    if getattr(s, "creator", None):
        resp.creator_name = s.creator.name
    return resp


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
    return [_build_source_response(s) for s in sources]


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
        return _build_source_response(source)
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
    return _build_source_response(source)


@router.post(
    "/sources/{source_id}/media",
    response_model=VideoSourceResponse,
    summary="Upload Authorized Media File for Source",
)
async def upload_source_media(
    source_id: int,
    request: Request,
    filename: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> VideoSourceResponse:
    source = await DiscoveryService.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video source not found")

    media_dir = Path(settings.MEDIA_DIR).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)

    header_filename = request.headers.get("x-filename") or filename or "uploaded_media.mp4"
    original_suffix = Path(header_filename).suffix.lower()
    if original_suffix not in (".mp4", ".mov", ".mkv", ".webm", ".avi"):
        original_suffix = ".mp4"

    dest_path = media_dir / f"source_{source.id}_{int(time.time())}{original_suffix}"
    total_bytes = 0
    with open(dest_path, "wb") as f_out:
        async for chunk in request.stream():
            f_out.write(chunk)
            total_bytes += len(chunk)

    if total_bytes == 0:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    source.local_video_path = str(dest_path)
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Auto-resume any intake batch item waiting on media for this source
    result = await db.execute(
        select(IntakeBatchItem).where(
            IntakeBatchItem.source_id == source.id,
            IntakeBatchItem.status.in_(["awaiting_media", "awaiting_authorized_media", "media_resolving", "received", "rights_verified"]),
        )
    )
    waiting_items = result.scalars().all()
    if waiting_items:
        from app.modules.orchestration.pipeline_engine import AutonomousPipelineService
        for item in waiting_items:
            try:
                await AutonomousPipelineService.process_item(db, item.id, auto_render_top=True)
            except Exception as e:
                logger.error(f"Error auto-processing resumed batch item {item.id}: {e}")

    return _build_source_response(source)


@router.post(
    "/sources/{source_id}/link-local",
    response_model=VideoSourceResponse,
    summary="Link Staged Local Media File to Source",
)
async def link_local_source_media(
    source_id: int,
    data: LinkLocalMediaInput,
    db: AsyncSession = Depends(get_db),
) -> VideoSourceResponse:
    source = await DiscoveryService.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video source not found")

    candidate_path = Path(data.local_path).expanduser().resolve()
    if not candidate_path.exists() or not candidate_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Local media file not found at path: {data.local_path}",
        )
    if candidate_path.stat().st_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local media file is empty (0 bytes).",
        )

    source.local_video_path = str(candidate_path)
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Auto-resume any intake batch item waiting on media for this source
    result = await db.execute(
        select(IntakeBatchItem).where(
            IntakeBatchItem.source_id == source.id,
            IntakeBatchItem.status.in_(["awaiting_media", "awaiting_authorized_media", "media_resolving", "received", "rights_verified"]),
        )
    )
    waiting_items = result.scalars().all()
    if waiting_items:
        from app.modules.orchestration.pipeline_engine import AutonomousPipelineService
        for item in waiting_items:
            try:
                await AutonomousPipelineService.process_item(db, item.id, auto_render_top=True)
            except Exception as e:
                logger.error(f"Error auto-processing resumed batch item {item.id}: {e}")

    return _build_source_response(source)


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
