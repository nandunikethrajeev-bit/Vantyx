"""VANTYX Distribution & YouTube Publishing Endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.distribution.service import (
    DistributionService,
    PublishingEligibilityError,
    TimezoneHelper,
)
from app.schemas.distribution import (
    DailySlotsResponse,
    OAuthCallbackRequest,
    OAuthUrlResponse,
    PublishScheduleCreate,
    PublishScheduleResponse,
    PublishTriggerResponse,
    YouTubeAccountResponse,
)

router = APIRouter(prefix="/distribution", tags=["Distribution & Publishing"])


# ---------------- Google OAuth 2.0 Endpoints ----------------

@router.get(
    "/oauth/url",
    response_model=OAuthUrlResponse,
    summary="Get Google OAuth 2.0 Authorization URL",
)
async def get_oauth_url(
    state: Optional[str] = Query(None, description="Optional CSRF state token")
) -> OAuthUrlResponse:
    info = DistributionService.get_oauth_authorization_url(state=state)
    return OAuthUrlResponse(**info)


@router.post(
    "/oauth/callback",
    response_model=YouTubeAccountResponse,
    summary="Handle OAuth Authorization Callback",
)
async def oauth_callback(
    data: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> YouTubeAccountResponse:
    try:
        account = await DistributionService.exchange_oauth_code(db, code=data.code, state=data.state)
        return YouTubeAccountResponse.model_validate(account)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth code exchange failed: {exc}",
        )


@router.get(
    "/oauth/status",
    summary="Get Connected YouTube Channel Identity",
)
async def get_channel_status(
    db: AsyncSession = Depends(get_db),
):
    account = await DistributionService.get_connected_account(db)
    if not account:
        return {
            "authorized": False,
            "channel": None,
            "message": "No active YouTube channel connected.",
        }
    return {
        "authorized": True,
        "channel": YouTubeAccountResponse.model_validate(account),
        "message": f"Connected to {account.channel_title}",
    }


@router.post(
    "/oauth/disconnect",
    summary="Disconnect YouTube Channel",
)
async def disconnect_channel(
    db: AsyncSession = Depends(get_db),
):
    disconnected = await DistributionService.disconnect_account(db)
    return {"success": disconnected, "message": "Channel disconnected successfully." if disconnected else "No active channel found."}


# ---------------- Scheduling Calendar Endpoints ----------------

@router.get(
    "/schedule/slots",
    response_model=DailySlotsResponse,
    summary="Get Daily Publishing Slots in Asia/Kolkata",
)
async def get_daily_slots(
    date: Optional[str] = Query(
        None,
        description="Target date in YYYY-MM-DD (defaults to today in Asia/Kolkata)",
    ),
    db: AsyncSession = Depends(get_db),
) -> DailySlotsResponse:
    if not date:
        now_kolkata = datetime.now(TimezoneHelper.KOLKATA_TZ)
        date = now_kolkata.strftime("%Y-%m-%d")

    return await DistributionService.get_daily_slots(db, date)


@router.post(
    "/schedule",
    response_model=PublishScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an Eligible Short for Release",
)
async def create_schedule(
    request: PublishScheduleCreate,
    db: AsyncSession = Depends(get_db),
) -> PublishScheduleResponse:
    try:
        schedule = await DistributionService.create_schedule(db, request)
        return PublishScheduleResponse.model_validate(schedule)
    except PublishingEligibilityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Scheduling failed: {exc}")


@router.get(
    "/schedule",
    response_model=List[PublishScheduleResponse],
    summary="List Scheduled Publications",
)
async def list_schedules(
    status: Optional[str] = Query(None, description="scheduled | publishing | published | failed | cancelled"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[PublishScheduleResponse]:
    schedules = await DistributionService.list_schedules(db, status=status, limit=limit)
    return [PublishScheduleResponse.model_validate(s) for s in schedules]


@router.get(
    "/schedule/{schedule_id}",
    response_model=PublishScheduleResponse,
    summary="Get Schedule Details",
)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
) -> PublishScheduleResponse:
    schedule = await DistributionService.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return PublishScheduleResponse.model_validate(schedule)


@router.delete(
    "/schedule/{schedule_id}",
    response_model=PublishScheduleResponse,
    summary="Cancel Publication Schedule",
)
async def cancel_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
) -> PublishScheduleResponse:
    try:
        schedule = await DistributionService.cancel_schedule(db, schedule_id)
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        return PublishScheduleResponse.model_validate(schedule)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ---------------- Video Upload & Publishing Endpoints ----------------

@router.post(
    "/publish/{schedule_id}",
    response_model=PublishTriggerResponse,
    summary="Execute YouTube Video Upload and Scheduled Publishing",
)
async def publish_video(
    schedule_id: int,
    force_mock: bool = Query(False, description="Force mock upload execution"),
    db: AsyncSession = Depends(get_db),
) -> PublishTriggerResponse:
    try:
        schedule = await DistributionService.execute_publishing_upload(
            db=db, schedule_id=schedule_id, force_mock=force_mock
        )
        return PublishTriggerResponse(
            schedule_id=schedule.id,
            status=schedule.status,
            youtube_video_id=schedule.youtube_video_id,
            publish_url=schedule.publish_url,
            is_mock=schedule.is_mock,
            message="Publication executed successfully" if schedule.status == "published" else f"Publication failed: {schedule.error_message}",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {exc}")
