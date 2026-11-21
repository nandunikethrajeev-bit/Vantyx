"""API v1 Endpoints for Analytics, Performance Intelligence & Feedback Engine."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.analytics import AnalyticsCollectionJob
from app.modules.analytics.service import AnalyticsService
from app.schemas.analytics import (
    AnalyticsCollectionJobResponse,
    ChannelAnalyticsResponse,
    FeedbackConfigUpdate,
    FeedbackStatusResponse,
    PerformanceIntelligenceResponse,
    PublishedVideoPerformanceResponse,
)

router = APIRouter(prefix="/analytics", tags=["Audience Analytics & Feedback"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_channel_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve channel-level audience metrics, latest snapshot, and 14-day historical trend."""
    return await AnalyticsService.get_channel_performance_overview(db)


@router.get("/videos", response_model=List[PublishedVideoPerformanceResponse])
async def get_published_videos_performance(
    db: AsyncSession = Depends(get_db),
) -> List[PublishedVideoPerformanceResponse]:
    """Retrieve granular performance, view retention, and profiles for all published Shorts."""
    return await AnalyticsService.get_published_videos_performance(db)


@router.get("/insights", response_model=PerformanceIntelligenceResponse)
async def get_performance_intelligence_insights(
    db: AsyncSession = Depends(get_db),
) -> PerformanceIntelligenceResponse:
    """Retrieve statistical intelligence report across hooks, durations, categories, and slots."""
    return await AnalyticsService.get_performance_intelligence_insights(db)


@router.post("/collect", response_model=AnalyticsCollectionJobResponse)
async def trigger_analytics_collection(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsCollectionJobResponse:
    """Trigger an immediate performance telemetry collection sweep from YouTube Analytics."""
    job = await AnalyticsService.run_collection_cycle(db, job_type="manual")
    return job


@router.get("/jobs", response_model=List[AnalyticsCollectionJobResponse])
async def list_analytics_collection_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[AnalyticsCollectionJobResponse]:
    """List historical analytics collection audit logs."""
    stmt = (
        select(AnalyticsCollectionJob)
        .order_by(AnalyticsCollectionJob.started_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/feedback/status", response_model=FeedbackStatusResponse)
async def get_feedback_engine_status(
    db: AsyncSession = Depends(get_db),
) -> FeedbackStatusResponse:
    """Retrieve current configuration and calibrated multipliers for the selection feedback loop."""
    return await AnalyticsService.get_feedback_multipliers(db)


@router.patch("/feedback/config", response_model=Dict[str, Any])
async def update_feedback_engine_config(
    payload: FeedbackConfigUpdate,
) -> Dict[str, Any]:
    """Update runtime configuration for the closed-loop selection feedback engine."""
    return await AnalyticsService.update_feedback_config(
        enabled=payload.feedback_enabled,
        max_impact=payload.max_impact,
        min_sample_size=payload.min_sample_size,
    )
