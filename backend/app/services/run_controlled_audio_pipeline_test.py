"""Execution script to validate the complete VANTYX audio intelligence pipeline with controlled synthetic audio."""

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
from app.modules.intelligence.audio_analyzer import AudioAnalyzer
from app.modules.selection.service import SelectionService
from app.modules.production.service import ProductionService
from app.modules.distribution.service import DistributionService, PublishingEligibilityError
from app.schemas.discovery import VideoSourceCreate
from app.schemas.distribution import PublishScheduleCreate
from app.schemas.production import RenderSettingsInput


async def main():
    print("=" * 80)
    print("VANTYX AUDIO INTELLIGENCE END-TO-END PIPELINE VALIDATION TEST")
    print("=" * 80)

    controlled_file = Path("data/media/controlled_audio_test_footage_1080p.mp4").resolve()
    print("\n[STAGE 0: INPUT CONTROLLED AUDIO TEST VIDEO INSPECTION]")
    print(f"Path: {controlled_file}")
    assert controlled_file.exists(), f"File does not exist: {controlled_file}"
    file_size = os.path.getsize(controlled_file)
    print(f"File Size: {file_size:,} bytes ({round(file_size / (1024*1024), 2)} MB)")

    ffmpeg_exe = settings.get_ffmpeg_executable()
    probe = subprocess.run([ffmpeg_exe, "-i", str(controlled_file)], capture_output=True, text=True)
    for line in probe.stderr.splitlines():
        if "Duration:" in line or "Stream #0:0" in line or "Stream #0:1" in line:
            print(f"  {line.strip()}")

    # Direct AudioAnalyzer Segment Probing
    print("\n[STAGE 0B: DIRECT ACOUSTIC SEGMENT ANALYSIS via AudioAnalyzer]")
    segments = [
        ("Scene 1: Stalking Prowl (Quiet Ambience)", 0.0, 15.0),
        ("Scene 2: Bank Vault Breach (Explosion Peak)", 15.0, 30.0),
        ("Scene 3: Downtown Shootout (Dynamic Alternating)", 30.0, 45.0),
        ("Scene 4: Stealth Rooftop Escape (Near-Silence)", 45.0, 60.0),
    ]
    for name, start, end in segments:
        m = AudioAnalyzer.analyze_scene_audio(controlled_file, start, end)
        print(f"  {name}:")
        print(f"    Window: [{start}s - {end}s] (Duration: {m.duration_seconds:.1f}s)")
        print(f"    RMS Level: {m.rms_db} dBFS | Peak Level: {m.peak_db} dBFS")
        print(f"    LRA: {m.loudness_range_lu} LU | Silence Ratio: {m.silence_ratio * 100:.1f}%")
        print(f"    Audio Score: {m.audio_score:.1f} / 100 | Tag: '{m.audio_tag}' | Silent: {m.is_silent}")

    session_maker = get_async_session_maker()
    async with session_maker() as db:
        # 1. Ingestion
        print("\n[STAGE 1: SOURCE REGISTRATION & INGESTION]")
        uid = uuid.uuid4().hex[:6]
        video_id = f"controlled_audio_val_{uid}"
        dto = VideoSourceCreate(
            video_id=video_id,
            title="SYNTHETIC_TEST_ONLY — Controlled Audio Intelligence Benchmark 1080p",
            description="Controlled 4-scene synthetic benchmark with varied RMS, peak transients, LRA, and silence.",
            duration_seconds=60,
            source_url=f"file:///{controlled_file.as_posix()}",
            local_video_path=str(controlled_file),
            discovery_method="synthetic_test",
            is_synthetic=True,
            is_own_gameplay=False,
        )
        source = await DiscoveryService.ingest_manual_source(db, dto)
        print(f"  Source Registered ID: {source.id}")
        print(f"  Video ID: {source.video_id}")
        print(f"  Title: {source.title}")
        print(f"  Duration: {source.duration_seconds}s")
        print(f"  Is Synthetic Flag: {source.is_synthetic}")
        print(f"  Rights Permission Status: {source.rights.permission_status if source.rights else None}")
        print(f"  Rights Commercial Allowed: {source.rights.commercial_use_allowed if source.rights else None}")
        print(f"  Rights Editing Scope: {source.rights.allowed_editing_scope if source.rights else None}")
        is_elig, elig_reason = DiscoveryService.evaluate_eligibility(source)
        print(f"  Eligibility Gate Check: eligible={is_elig}, reason='{elig_reason}'")

        # 2. Intelligence & Audio Analysis
        print("\n[STAGE 2: SCENE DETECTION & AUDIO INTELLIGENCE]")
        job = await IntelligenceService.start_video_analysis(db, source.id, force=True)
        print(f"  Analysis Job ID: {job.id}")
        print(f"  Status: {job.status}")
        print(f"  Provider Used: {job.provider}")
        raw = job.raw_result or {}
        print(f"  Detection Method: {raw.get('detection_method')}")
        print(f"  Visual Cuts Detected: {raw.get('visual_cuts_detected')}")
        print(f"  Capabilities: {json.dumps(raw.get('capabilities', {}))}")
        print(f"  Track Metrics: {json.dumps(raw.get('audio_track_metrics', {}))}")
        print(f"  Detected Scenes Count: {len(job.scenes)}")
        for idx, scene in enumerate(job.scenes, 1):
            am = scene.audio_metrics or {}
            print(f"    Scene {idx}: [{scene.start_time:.1f}s - {scene.end_time:.1f}s]")
            print(f"      Label: '{scene.scene_label}'")
            print(f"      Action Intensity: {scene.action_intensity:.2f} | Excitement: {scene.excitement_score:.2f}")
            print(f"      Audio Metrics -> RMS: {am.get('rms_db')} dBFS, Peak: {am.get('peak_db')} dBFS, "
                  f"LRA: {am.get('lra_lu')} LU, Silence: {am.get('silence_ratio', 0)*100:.1f}%, "
                  f"Score: {am.get('audio_score')}/100, Tag: '{am.get('audio_tag')}'")

        # 3. Candidate Clip Selection & Scoring
        print("\n[STAGE 3: CANDIDATE CLIP SELECTION & SCORING]")
        candidates = await SelectionService.generate_candidates_for_source(
            db, source.id, min_score_threshold=15.0, max_candidates=5
        )
        print(f"  Generated Candidates Count: {len(candidates)}")
        for c in candidates:
            print(f"    Candidate #{c.id}: [{c.start_time:.1f}s - {c.end_time:.1f}s] Duration: {c.duration_seconds:.1f}s")
            print(f"      Title: '{c.title_suggestion}'")
            print(f"      Scores -> Hook: {c.hook_score:.1f}, Retention: {c.retention_score:.1f}, "
                  f"Context: {c.context_score:.1f}, Audio: {c.audio_score:.1f} | Overall: {c.overall_score:.1f}")
            print(f"      Rationale: {c.rationale}")

        assert len(candidates) > 0, "No candidates generated"
        selected_candidate = candidates[0]

        # 4. 9:16 Vertical Video Production
        print("\n[STAGE 4: 9:16 VERTICAL PRODUCTION & RENDERING]")
        print(f"  Rendering Top Candidate #{selected_candidate.id} ({selected_candidate.start_time:.1f}s - {selected_candidate.end_time:.1f}s)...")
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

        # Verify rendered audio stream
        probe_rendered = subprocess.run([ffmpeg_exe, "-i", str(rendered_file)], capture_output=True, text=True)
        print("  Rendered Output Streams:")
        for line in probe_rendered.stderr.splitlines():
            if "Duration:" in line or "Stream #0:0" in line or "Stream #0:1" in line:
                print(f"    {line.strip()}")

        # 5. Publishing Safety Gate Enforcement
        print("\n[STAGE 5: PUBLISHING SAFETY GATE VERIFICATION]")
        sched_request = PublishScheduleCreate(
            candidate_id=selected_candidate.id,
            render_job_id=render_job.id,
            target_date="2027-10-01",
            slot_name="15:00",
            title="SYNTHETIC_TEST_ONLY - Blocked Schedule Attempt",
        )
        try:
            await DistributionService.create_schedule(db, sched_request)
            raise AssertionError("CRITICAL: Synthetic media scheduling SUCCEEDED when it should have been BLOCKED!")
        except PublishingEligibilityError as exc:
            print(f"  SUCCESS: Scheduling Gate strictly BLOCKED synthetic release as required!")
            print(f"  Rejection Reason: {exc}")

        print("\n" + "=" * 80)
        print("CONTROLLED AUDIO INTELLIGENCE PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
