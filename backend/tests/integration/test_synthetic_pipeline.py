"""Integration test validating the full synthetic media processing pipeline and publishing safety gate."""

import os
import uuid
import pytest
import subprocess
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.source import VideoSource
from app.db.models.production import RenderJob
from app.db.models.selection import CandidateClip
from app.modules.discovery.service import DiscoveryService
from app.modules.distribution.service import DistributionService, PublishingEligibilityError
from app.modules.intelligence.service import IntelligenceService
from app.modules.production.service import ProductionService
from app.modules.selection.service import SelectionService
from app.schemas.discovery import VideoSourceCreate
from app.schemas.distribution import PublishScheduleCreate
from app.schemas.production import RenderSettingsInput


@pytest.mark.asyncio
async def test_synthetic_media_full_pipeline_and_safety_gate(async_db_session: AsyncSession):
    """End-to-end verification of synthetic media through Discovery -> Intelligence -> Selection -> Production -> Distribution safety gate."""
    synthetic_file = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
    assert synthetic_file.exists(), f"Synthetic test footage missing at {synthetic_file}"
    assert os.path.getsize(synthetic_file) > 100_000, "Synthetic video file is truncated"

    uid = uuid.uuid4().hex[:8]
    test_video_id = f"synth_test_{uid}"

    # 1. Ingest Synthetic Source
    create_dto = VideoSourceCreate(
        video_id=test_video_id,
        title="SYNTHETIC_TEST_ONLY — NOT REAL GAMEPLAY — GTA 6 Lab",
        description="Synthetic 60s multi-scene test video for media pipeline verification",
        duration_seconds=60,
        source_url=f"file:///{synthetic_file.as_posix()}",
        local_video_path=str(synthetic_file),
        discovery_method="synthetic_test",
        is_synthetic=True,
        is_own_gameplay=True,
    )
    source = await DiscoveryService.ingest_manual_source(async_db_session, create_dto)
    assert source.id is not None
    assert source.is_synthetic is True
    assert source.local_video_path == str(synthetic_file)
    assert source.rights is not None
    assert source.rights.permission_status == "synthetic_test"
    assert source.rights.commercial_use_allowed is False
    assert source.rights.allowed_editing_scope == "restricted"

    # Evaluate eligibility gate
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is False
    assert "ineligible" in reason.lower()

    # 2. Scene Detection & AI Analysis with FFmpeg Visual Cut Boundaries
    analysis_job = await IntelligenceService.start_video_analysis(async_db_session, source.id, force=True)
    assert analysis_job.status == "completed"
    assert len(analysis_job.scenes) == 4, f"Expected 4 FFmpeg-detected scenes, got {len(analysis_job.scenes)}"
    assert analysis_job.raw_result["detection_method"] == "ffmpeg_visual_cuts"
    assert analysis_job.raw_result["visual_cuts_detected"] == 3
    assert analysis_job.raw_result["capabilities"]["visual_scene_detection"] is True
    assert analysis_job.raw_result["capabilities"]["audio_analysis"] is True
    assert analysis_job.raw_result["capabilities"]["video_frame_understanding"] is False
    assert analysis_job.raw_result["capabilities"]["speech_transcription"] is False
    assert analysis_job.raw_result["audio_track_metrics"]["has_audio_stream"] is True
    assert analysis_job.raw_result["audio_track_metrics"]["rms_energy_db"] is not None

    # Verify exact scene boundaries from FFmpeg cuts (15s per scene)
    scene_starts = [s.start_time for s in analysis_job.scenes]
    assert scene_starts == [0.0, 15.0, 30.0, 45.0]

    for sc in analysis_job.scenes:
        assert sc.speech_transcript is None, "Speech transcript must not be fabricated"
        assert "visual_cut" in sc.tags
        assert sc.audio_metrics is not None, "Acoustic metrics must be measured on local media"
        assert sc.audio_metrics["has_audio"] is True
        assert sc.audio_metrics["rms_db"] is not None

    # 3. Candidate Clip Selection & Scoring
    candidates = await SelectionService.generate_candidates_for_source(
        async_db_session, source.id, min_score_threshold=20.0, max_candidates=4
    )
    assert len(candidates) > 0
    candidate = candidates[0]
    assert 15.0 <= candidate.duration_seconds <= 60.0
    assert candidate.overall_score > 0.0

    # 4. 9:16 Vertical Video Production
    render_job = await ProductionService.execute_render(
        async_db_session,
        candidate_id=candidate.id,
        render_settings=RenderSettingsInput(layout_style="blurred_backdrop"),
    )
    assert render_job.status == "completed"
    assert render_job.is_synthetic is True
    assert render_job.format_aspect == "9:16"
    assert render_job.output_file_path is not None
    assert os.path.exists(render_job.output_file_path)
    assert os.path.getsize(render_job.output_file_path) > 100_000

    # Probe rendered output with FFmpeg to verify 9:16 resolution and playability
    ffmpeg_exe = settings.get_ffmpeg_executable()
    probe_cmd = [ffmpeg_exe, "-i", render_job.output_file_path]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
    stderr_out = probe_res.stderr
    assert "1080x1920" in stderr_out, f"Expected 1080x1920 resolution in rendered output: {stderr_out}"
    assert "aac" in stderr_out.lower(), "Expected audio stream in rendered output"

    # 5. Strict Publishing Safety Gate Enforcement
    # 5a. Attempting to schedule this synthetic clip must be strictly rejected
    sched_request = PublishScheduleCreate(
        candidate_id=candidate.id,
        render_job_id=render_job.id,
        target_date="2027-08-20",
        slot_name="13:00",
        title="SYNTHETIC_TEST_ONLY Should Fail Release",
    )
    with pytest.raises(PublishingEligibilityError, match="Synthetic test media is strictly prohibited"):
        await DistributionService.create_schedule(async_db_session, sched_request)

    # 5b. Attempting direct upload execution must also be rejected by defense-in-depth gate
    from app.db.models.distribution import PublishSchedule
    from datetime import datetime, timezone
    bypassed_schedule = PublishSchedule(
        candidate_id=candidate.id,
        render_job_id=render_job.id,
        scheduled_time=datetime.now(timezone.utc),
        slot_name="13:00",
        timezone="Asia/Kolkata",
        target_channel=settings.PRIMARY_CHANNEL_NAME,
        title="Bypassed Synthetic Release Attempt",
        description="Testing direct upload failure",
        tags="test",
        privacy_status="private",
        status="scheduled",
        is_mock=True,
    )
    async_db_session.add(bypassed_schedule)
    await async_db_session.commit()
    await async_db_session.refresh(bypassed_schedule)

    with pytest.raises(PublishingEligibilityError, match="Media is classified as synthetic test media"):
        await DistributionService.execute_publishing_upload(async_db_session, bypassed_schedule.id)
