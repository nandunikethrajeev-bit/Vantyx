"""End-to-End Integration Test for VANTYX Autonomous URL-First Pipeline.

Tests the complete flow:
1. YouTube URL submission via batch intake
2. Compliant metadata resolution
3. Rights verification against registered creator
4. Media resolution to staged local video file
5. Intelligence analysis (FFmpeg visual scene cuts + audio energy metrics)
6. Selection scoring (hook, retention, audio scores)
7. Production rendering (9:16 vertical Short 1080x1920)
8. Output validation (file existence on disk, file size > 1024 bytes)
9. Output gallery query (GET /api/v1/production/outputs)
10. Stream with 206 Accept-Ranges & Download endpoints
11. Truthful handling of missing media and unauthorized rights
"""

import os
import shutil
import uuid
from pathlib import Path
import pytest
from starlette.testclient import TestClient


class TestAutonomousUrlPipeline:
    """Validate full autonomous URL workflow from URL intake to playable 9:16 Short."""

    def test_full_autonomous_url_to_short_workflow(self, sync_client: TestClient):
        # Verify synthetic test media is available
        synthetic_source_file = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
        assert synthetic_source_file.exists(), "Synthetic test video must exist for E2E testing"

        uid = uuid.uuid4().hex[:6]
        channel_id = f"UC_e2e_creator_{uid}"
        video_id = f"e2e_{uid}____"[:11]

        # 1. Register an approved partner creator in the DB
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Stunt Legend {uid}",
                "channel_id": channel_id,
                "content_category": "GTA Stunts",
                "approval_status": "approved",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201, f"Creator creation failed: {c_resp.text}"
        creator_id = c_resp.json()["id"]

        # 2. Stage media file so LocalStagedMediaResolver can resolve it for this video_id
        staged_dir = Path("data/media")
        staged_dir.mkdir(parents=True, exist_ok=True)
        staged_copy = staged_dir / f"test_{video_id}_source.mp4"
        shutil.copyfile(synthetic_source_file, staged_copy)

        try:
            # 3. Submit YouTube URL through batch intake with auto_process=True
            url = f"https://www.youtube.com/watch?v={video_id}"
            intake_resp = sync_client.post(
                "/api/v1/discovery/sources/batch?auto_process=true",
                json={
                    "creator_id": creator_id,
                    "urls": [url],
                    "notes": f"Autonomous E2E Run {uid}",
                },
            )
            assert intake_resp.status_code == 201
            batch_data = intake_resp.json()
            assert batch_data["total_valid"] == 1
            batch_id = batch_data["batch_id"]

            # 4. Fetch the batch and verify the item completed through all stages
            batch_poll = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
            assert batch_poll.status_code == 200
            items = batch_poll.json()["items"]
            assert len(items) == 1
            item = items[0]

            assert item["video_id"] == video_id
            assert item["status"] == "completed"
            assert item["commercial_use_allowed"] is True
            source_id = item["source_id"]
            assert source_id is not None

            # 5. Verify the source was analyzed and has scenes
            intel_resp = sync_client.get(f"/api/v1/intelligence/sources/{source_id}/scenes")
            assert intel_resp.status_code == 200
            scenes = intel_resp.json()
            assert len(scenes) >= 1
            first_scene = scenes[0]
            assert "audio_metrics" in first_scene or first_scene.get("duration_seconds", 0) > 0

            # 6. Verify candidate moments were ranked
            sel_resp = sync_client.get(f"/api/v1/selection/candidates?source_id={source_id}")
            assert sel_resp.status_code == 200
            candidates = sel_resp.json()
            assert len(candidates) >= 1
            top_candidate = candidates[0]
            assert top_candidate["overall_score"] > 0
            assert top_candidate["status"] in ("approved", "selected", "pending", "produced")

            # 7. Check Unified Outputs Studio API
            outputs_resp = sync_client.get("/api/v1/production/outputs?limit=20")
            assert outputs_resp.status_code == 200
            outputs = outputs_resp.json()
            assert len(outputs) >= 1

            matched_output = next((o for o in outputs if o["source_id"] == source_id), None)
            assert matched_output is not None, "Rendered short must appear in unified outputs gallery"
            assert matched_output["status"] == "completed"
            assert matched_output["file_exists"] is True
            assert matched_output["file_size_mb"] > 0
            assert matched_output["resolution"] == "1080x1920"

            job_id = matched_output["job_id"]

            # 8. Test Video Range Stream Endpoint (200 / 206 with Accept-Ranges)
            stream_resp = sync_client.get(f"/api/v1/production/jobs/{job_id}/stream")
            assert stream_resp.status_code in (200, 206)
            assert "bytes" in stream_resp.headers.get("accept-ranges", "").lower()

            # 9. Test Video Download Endpoint
            download_resp = sync_client.get(f"/api/v1/production/jobs/{job_id}/download")
            assert download_resp.status_code == 200
            assert "attachment" in download_resp.headers.get("content-disposition", "")
            assert len(download_resp.content) > 1024

        finally:
            if staged_copy.exists():
                staged_copy.unlink()

    def test_autonomous_pipeline_missing_media_safeguard(self, sync_client: TestClient):
        """When source media cannot be located on disk, pipeline halts safely at awaiting_media."""
        uid = uuid.uuid4().hex[:6]
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Creator Without Media {uid}",
                "channel_id": f"UC_nomedia_{uid}",
                "content_category": "GTA Stunts",
                "approval_status": "approved",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        non_staged_vid = f"nomedia_{uid}"[:11]
        url = f"https://www.youtube.com/watch?v={non_staged_vid}"

        intake_resp = sync_client.post(
            "/api/v1/discovery/sources/batch?auto_process=true",
            json={
                "creator_id": creator_id,
                "urls": [url],
            },
        )
        assert intake_resp.status_code == 201
        batch_id = intake_resp.json()["batch_id"]

        batch_poll = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
        items = batch_poll.json()["items"]
        assert len(items) == 1
        item = items[0]

        # Pipeline correctly halts at awaiting_authorized_media without crashing or generating fake renders
        assert item["status"] in ("awaiting_authorized_media", "awaiting_media")
        assert (
            "No authorized original media file found" in (item["error_message"] or "")
            or "creator-connected vault or authorized asset mapping" in (item["error_message"] or "")
            or "Media must be resolved" in (item["error_message"] or "")
        )

    def test_autonomous_pipeline_unverified_rights_safeguard(self, sync_client: TestClient):
        """When rights are unverified or non-commercial, pipeline halts before media analysis."""
        uid = uuid.uuid4().hex[:6]
        # Unapproved or restricted creator
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Restricted Creator {uid}",
                "channel_id": f"UC_restricted_{uid}",
                "content_category": "GTA Stunts",
                "approval_status": "rejected",
                "permission_tier": "unverified",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        restricted_vid = f"restr_{uid}___"[:11]
        url = f"https://www.youtube.com/watch?v={restricted_vid}"

        intake_resp = sync_client.post(
            "/api/v1/discovery/sources/batch?auto_process=true",
            json={
                "creator_id": creator_id,
                "urls": [url],
            },
        )
        assert intake_resp.status_code == 201
        batch_id = intake_resp.json()["batch_id"]

        batch_poll = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
        items = batch_poll.json()["items"]
        assert len(items) == 1
        item = items[0]

        # Pipeline must halt at rights check
        assert item["commercial_use_allowed"] is False
        assert item["status"] in ("rejected", "rights_pending", "failed")
