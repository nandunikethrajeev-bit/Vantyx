"""Unit tests for VANTYX Analytics Intelligence & Performance Feedback Engine."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analytics import (
    ChannelAnalyticsSnapshot,
    ClipPerformanceProfile,
    VideoAnalyticsSnapshot,
)
from app.db.models.distribution import PublishSchedule
from app.db.models.intelligence import VideoScene
from app.db.models.production import RenderJob
from app.db.models.selection import CandidateClip
from app.db.models.source import VideoSource
from app.modules.analytics.service import AnalyticsService
from app.modules.selection.service import RankingWeights, SelectionService


@pytest.mark.asyncio
async def test_analytics_collection_and_snapshot_deduplication(async_db_session: AsyncSession):
    """Verify that multiple collection runs on the same date update snapshots without duplicating rows."""
    unique_id = uuid.uuid4().hex[:8]
    test_video_id = f"yt_test_{unique_id}"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Create dummy source, candidate, render, and published schedule
    source = VideoSource(
        video_id=f"vid_{unique_id}",
        title="GTA 6 Heist Showcase",
        duration_seconds=300,
        source_url=f"https://www.youtube.com/watch?v={unique_id}",
        discovery_method="manual_import",
        is_synthetic=False,
    )
    async_db_session.add(source)
    await async_db_session.commit()
    await async_db_session.refresh(source)

    candidate = CandidateClip(
        source_id=source.id,
        start_time=10.0,
        end_time=45.0,
        duration_seconds=35.0,
        title_suggestion="GTA 6: Crazy Bank Heist #Shorts",
        hook_score=85.0,
        retention_score=82.0,
        context_score=75.0,
        audio_score=78.0,
        overall_score=80.0,
        status="approved",
    )
    async_db_session.add(candidate)
    await async_db_session.commit()
    await async_db_session.refresh(candidate)

    render_job = RenderJob(
        candidate_id=candidate.id,
        source_id=source.id,
        status="completed",
        progress_pct=100.0,
        output_file_path=f"storage/rendered_{unique_id}.mp4",
        is_synthetic=False,
    )
    async_db_session.add(render_job)
    await async_db_session.commit()
    await async_db_session.refresh(render_job)

    schedule = PublishSchedule(
        render_job_id=render_job.id,
        candidate_id=candidate.id,
        scheduled_time=datetime.now(timezone.utc) - timedelta(days=3),
        slot_name="09:00",
        timezone="Asia/Kolkata",
        target_channel="Astro Rebel",
        title="GTA 6: Crazy Bank Heist #Shorts",
        status="published",
        youtube_video_id=test_video_id,
        is_mock=True,
    )
    async_db_session.add(schedule)
    await async_db_session.commit()
    await async_db_session.refresh(schedule)

    # First collection pass
    job1 = await AnalyticsService.run_collection_cycle(async_db_session, job_type="unit_test_1")
    assert job1.status == "completed"

    count_stmt = select(VideoAnalyticsSnapshot).where(
        VideoAnalyticsSnapshot.youtube_video_id == test_video_id,
        VideoAnalyticsSnapshot.snapshot_date == today_str,
    )
    snapshots_pass1 = list((await async_db_session.execute(count_stmt)).scalars().all())
    assert len(snapshots_pass1) == 1
    initial_views = snapshots_pass1[0].views
    assert initial_views > 0

    # Second collection pass on the same date (deduplication check)
    job2 = await AnalyticsService.run_collection_cycle(async_db_session, job_type="unit_test_2")
    assert job2.status == "completed"

    snapshots_pass2 = list((await async_db_session.execute(count_stmt)).scalars().all())
    assert len(snapshots_pass2) == 1  # No duplicate rows created!


@pytest.mark.asyncio
async def test_delayed_reporting_handling(async_db_session: AsyncSession):
    """Verify that videos published under 48 hours ago are flagged as delayed reporting."""
    unique_id = uuid.uuid4().hex[:8]
    recent_video_id = f"yt_recent_{unique_id}"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Schedule published 6 hours ago
    schedule = PublishSchedule(
        render_job_id=1,
        candidate_id=1,
        scheduled_time=datetime.now(timezone.utc) - timedelta(hours=6),
        slot_name="13:00",
        timezone="Asia/Kolkata",
        target_channel="Astro Rebel",
        title="GTA 6: Recent Cop Chase #Shorts",
        status="published",
        youtube_video_id=recent_video_id,
        is_mock=True,
    )
    async_db_session.add(schedule)
    await async_db_session.commit()
    await async_db_session.refresh(schedule)

    await AnalyticsService._collect_video_snapshot(async_db_session, schedule, today_str)

    stmt = select(VideoAnalyticsSnapshot).where(
        VideoAnalyticsSnapshot.youtube_video_id == recent_video_id
    )
    snapshot = (await async_db_session.execute(stmt)).scalars().first()
    assert snapshot is not None
    assert snapshot.is_delayed_reporting is True
    assert snapshot.reporting_status == "delayed"


@pytest.mark.asyncio
async def test_clip_performance_profile_and_multiplier_bounds(async_db_session: AsyncSession):
    """Verify that feedback multipliers stay strictly bounded within max_impact limits."""
    unique_id = uuid.uuid4().hex[:8]
    schedule = PublishSchedule(
        render_job_id=1,
        candidate_id=1,
        scheduled_time=datetime.now(timezone.utc) - timedelta(days=5),
        slot_name="17:00",
        timezone="Asia/Kolkata",
        target_channel="Astro Rebel",
        title="GTA 6: Mega Jet Stunt #Shorts",
        status="published",
        youtube_video_id=f"yt_stunt_{unique_id}",
        is_mock=True,
    )
    async_db_session.add(schedule)
    await async_db_session.commit()

    profile = await AnalyticsService._upsert_clip_performance_profile(
        async_db_session,
        candidate_id=schedule.candidate_id,
        schedule_id=schedule.id,
        views=25000,
        avp=95.0,  # Extremely high retention
        age_hours=120.0,
        slot_name="17:00",
        title="GTA 6: Mega Jet Stunt #Shorts",
    )

    assert profile.duration_bucket in ["15-25s", "25-35s", "35-45s", "45-60s"]
    assert profile.content_category == "stunt"
    # Even with 95% retention, multiplier cannot exceed 1.0 + max_impact (e.g. 1.15)
    assert 0.85 <= profile.feedback_multiplier <= 1.15


@pytest.mark.asyncio
async def test_selection_feedback_integration_and_explainable_rationale():
    """Verify that SelectionService applies bounded feedback modifiers and explains them."""
    scene = VideoScene(
        source_id=1,
        start_time=0.0,
        end_time=32.0,
        scene_label="GTA 6 Bank Vault Heist",
        action_intensity=0.85,
        excitement_score=0.80,
        speech_transcript="Move the cash bags into the getaway car now!",
        tags=["heist", "wanted", "action"],
    )

    weights = RankingWeights()

    # 1. Base scoring without feedback
    base_scores = SelectionService.calculate_scores(scene, weights, feedback_multipliers=None)
    base_overall = base_scores[4]
    base_rationale = base_scores[5]
    assert "Analytics Feedback" not in base_rationale

    # 2. Scoring with +10% heist feedback boost
    feedback_config = {
        "feedback_enabled": True,
        "max_impact": 0.15,
        "category_multipliers": {"heist": 1.10},
        "duration_multipliers": {"25-35s": 1.00},
    }

    boosted_scores = SelectionService.calculate_scores(
        scene, weights, feedback_multipliers=feedback_config
    )
    boosted_overall = boosted_scores[4]
    boosted_rationale = boosted_scores[5]

    assert boosted_overall > base_overall
    assert "Analytics Feedback" in boosted_rationale
    assert "calibrated modifier for heist" in boosted_rationale
