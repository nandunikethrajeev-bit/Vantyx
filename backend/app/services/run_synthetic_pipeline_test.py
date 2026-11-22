"""Standalone execution script to run the real synthetic media pipeline end-to-end and report detailed properties."""

import asyncio
import os
import subprocess
import json
import uuid
from pathlib import Path

from app.core.config import settings
from app.db.session import get_async_session_maker
from app.modules.discovery.service import DiscoveryService
from app.modules.intelligence.service import IntelligenceService
from app.modules.selection.service import SelectionService
from app.modules.production.service import ProductionService
from app.modules.distribution.service import DistributionService, PublishingEligibilityError
from app.schemas.discovery import VideoSourceCreate
from app.schemas.distribution import PublishScheduleCreate
from app.schemas.production import RenderSettingsInput


async def main():
    print("=" * 60)
    print("VANTYX SYNTHETIC MEDIA PIPELINE VALIDATION TEST")
    print("=" * 60)

    synthetic_file = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
    print(f"\n[STAGE 0: INPUT SYNTHETIC VIDEO INSPECTION]")
    print(f"Path: {synthetic_file}")
    print(f"Exists: {synthetic_file.exists()}")
    file_size = os.path.getsize(synthetic_file)
    print(f"File Size: {file_size:,} bytes ({round(file_size / (1024*1024), 2)} MB)")

    ffmpeg_exe = settings.get_ffmpeg_executable()
    probe = subprocess.run([ffmpeg_exe, "-i", str(synthetic_file)], capture_output=True, text=True)
    for line in probe.stderr.splitlines():
        if "Duration:" in line or "Stream #0:0" in line or "Stream #0:1" in line or "title" in line:
            print(f"  {line.strip()}")

    session_maker = get_async_session_maker()
    async with session_maker() as db:
        # 1. Ingestion
        print(f"\n[STAGE 1: SOURCE REGISTRATION & INGESTION]")
        uid = uuid.uuid4().hex[:6]
        video_id = f"synthetic_pipeline_{uid}"
        dto = VideoSourceCreate(
            video_id=video_id,
            title="SYNTHETIC_TEST_ONLY — NOT REAL GAMEPLAY — Vice City Heist & Pursuit Lab",
            description="Automated synthetic 60s footage generated via FFmpeg for pipeline validation.",
            duration_seconds=60,
            source_url=f"file:///{synthetic_file.as_posix()}",
            local_video_path=str(synthetic_file),
            discovery_method="synthetic_test",
            is_synthetic=True,
            is_own_gameplay=True,
        )
        source = await DiscoveryService.ingest_manual_source(db, dto)
        print(f"  Source Registered ID: {source.id}")
        print(f"  Video ID: {source.video_id}")
        print(f"  Title: {source.title}")
        print(f"  Duration: {source.duration_seconds}s")
        print(f"  Is Synthetic Flag: {source.is_synthetic}")
        print(f"  Local Video Path: {source.local_video_path}")
        print(f"  Rights Permission Status: {source.rights.permission_status if source.rights else None}")
        print(f"  Rights Commercial Allowed: {source.rights.commercial_use_allowed if source.rights else None}")
        print(f"  Rights Editing Scope: {source.rights.allowed_editing_scope if source.rights else None}")
        is_elig, elig_reason = DiscoveryService.evaluate_eligibility(source)
        print(f"  Eligibility Gate Check: eligible={is_elig}, reason='{elig_reason}'")

        # 2. Intelligence & Scene Detection
        print(f"\n[STAGE 2: SCENE DETECTION & AI INTELLIGENCE]")
        job = await IntelligenceService.start_video_analysis(db, source.id, force=True)
        print(f"  Analysis Job ID: {job.id}")
        print(f"  Status: {job.status}")
        print(f"  Provider Used: {job.provider}")
        raw = job.raw_result or {}
        print(f"  Detection Method: {raw.get('detection_method')}")
        print(f"  Visual Cuts Detected: {raw.get('visual_cuts_detected')}")
        print(f"  Capabilities: {json.dumps(raw.get('capabilities', {}))}")
        print(f"  Audio Track Metrics: {json.dumps(raw.get('audio_track_metrics', {}))}")
        print(f"  Detected Scenes Count: {len(job.scenes)}")
        for idx, scene in enumerate(job.scenes, 1):
            am = scene.audio_metrics or {}
            print(f"    Scene {idx}: [{scene.start_time:.1f}s - {scene.end_time:.1f}s] "
                  f"Label: '{scene.scene_label}' (Action: {scene.action_intensity:.2f}, Excitement: {scene.excitement_score:.2f}) "
                  f"Audio: [RMS: {am.get('rms_db')}dB, Peak: {am.get('peak_db')}dB, Score: {am.get('audio_score')}/100, Tag: {am.get('audio_tag')}]")

        # 3. Candidate Clip Selection & Scoring
        print(f"\n[STAGE 3: CANDIDATE CLIP SELECTION & SCORING]")
        candidates = await SelectionService.generate_candidates_for_source(
            db, source.id, min_score_threshold=20.0, max_candidates=4
        )
        print(f"  Generated Candidates Count: {len(candidates)}")
        for c in candidates:
            print(f"    Candidate #{c.id}: [{c.start_time:.1f}s - {c.end_time:.1f}s] Duration: {c.duration_seconds:.1f}s")
            print(f"      Title: '{c.title_suggestion}'")
            print(f"      Scores -> Hook: {c.hook_score:.1f}, Retention: {c.retention_score:.1f}, Overall: {c.overall_score:.1f}")

        assert len(candidates) > 0, "No candidates generated"
        selected_candidate = candidates[0]

        # 4. 9:16 Vertical Video Production
        print(f"\n[STAGE 4: 9:16 VERTICAL PRODUCTION & RENDERING]")
        print(f"  Rendering Candidate #{selected_candidate.id} ({selected_candidate.start_time:.1f}s - {selected_candidate.end_time:.1f}s)...")
        render_settings = RenderSettingsInput(layout_style="blurred_backdrop")
        render_job = await ProductionService.execute_render(db, selected_candidate.id, render_settings)
        print(f"  Render Job ID: {render_job.id}")
        print(f"  Render Status: {render_job.status}")
        print(f"  Is Synthetic Flag: {render_job.is_synthetic}")
        print(f"  Resolution: {render_job.resolution}")
        print(f"  Aspect Ratio: {render_job.format_aspect}")
        print(f"  Output Path: {render_job.output_file_path}")

        rendered_file = Path(render_job.output_file_path)
        assert rendered_file.exists(), "Rendered output file does not exist on disk"
        r_size = os.path.getsize(rendered_file)
        print(f"  Rendered Output Size: {r_size:,} bytes ({round(r_size / (1024*1024), 2)} MB)")

        # Verify rendered output metadata with FFmpeg
        probe_rendered = subprocess.run([ffmpeg_exe, "-i", str(rendered_file)], capture_output=True, text=True)
        print(f"  Rendered Output Stream Probing:")
        for line in probe_rendered.stderr.splitlines():
            if "Duration:" in line or "Stream #0:0" in line or "Stream #0:1" in line:
                print(f"    {line.strip()}")

        # 5. Publishing Safety Gate Enforcement
        print(f"\n[STAGE 5: PUBLISHING SAFETY GATE VERIFICATION]")
        print("  5a. Attempting to schedule synthetic video for YouTube distribution release...")
        sched_request = PublishScheduleCreate(
            candidate_id=selected_candidate.id,
            render_job_id=render_job.id,
            target_date="2027-09-01",
            slot_name="13:00",
            title="SYNTHETIC_TEST_ONLY - Should Be Blocked",
        )
        try:
            await DistributionService.create_schedule(db, sched_request)
            print("  CRITICAL ERROR: Synthetic media scheduling SUCCEEDED when it should have been BLOCKED!")
            raise AssertionError("Safety gate failed!")
        except PublishingEligibilityError as exc:
            print(f"  SUCCESS: Scheduling Gate strictly BLOCKED synthetic release as required!")
            print(f"  Rejection Reason: {exc}")

        print("  5b. Attempting direct upload execution via bypassed schedule...")
        from app.db.models.distribution import PublishSchedule
        from datetime import datetime, timezone
        bypassed_sched = PublishSchedule(
            candidate_id=selected_candidate.id,
            render_job_id=render_job.id,
            scheduled_time=datetime.now(timezone.utc),
            slot_name="13:00",
            timezone="Asia/Kolkata",
            target_channel=settings.PRIMARY_CHANNEL_NAME,
            title="Bypassed Release Attempt",
            description="Testing direct upload failure",
            tags="test",
            privacy_status="private",
            status="scheduled",
            is_mock=True,
        )
        db.add(bypassed_sched)
        await db.commit()
        await db.refresh(bypassed_sched)

        try:
            await DistributionService.execute_publishing_upload(db, bypassed_sched.id)
            print("  CRITICAL ERROR: Synthetic media upload SUCCEEDED when it should have been BLOCKED!")
            raise AssertionError("Safety gate failed!")
        except PublishingEligibilityError as exc:
            print(f"  SUCCESS: Upload Gate strictly BLOCKED synthetic upload as required!")
            print(f"  Rejection Reason: {exc}")

        print("\n" + "=" * 60)
        print("FULL SYNTHETIC MEDIA PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
