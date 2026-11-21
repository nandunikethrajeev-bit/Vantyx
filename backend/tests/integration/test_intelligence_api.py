"""Integration tests for AI Intelligence API endpoints and Eligibility Gating."""

import uuid
import pytest
from starlette.testclient import TestClient


def test_ai_analysis_workflow_and_eligibility_enforcement(sync_client: TestClient):
    """Verify that only legally eligible sources can be analyzed by AI engine."""
    uid = uuid.uuid4().hex[:6]

    # 1. Ingest an unverified source (without commercial rights)
    unverified_vid = f"yt_blocked_{uid}"
    unverified_payload = {
        "video_id": unverified_vid,
        "title": "Unverified Random Gameplay Upload",
        "duration_seconds": 240,
        "source_url": f"https://youtube.com/watch?v={unverified_vid}",
        "is_own_gameplay": False,
    }
    resp1 = sync_client.post("/api/v1/discovery/sources", json=unverified_payload)
    assert resp1.status_code == 201
    unverified_id = resp1.json()["id"]

    # Revoke commercial rights explicitly
    sync_client.put(
        f"/api/v1/discovery/sources/{unverified_id}/rights",
        json={"permission_status": "pending", "commercial_use_allowed": False},
    )

    # 2. Attempt to trigger AI analysis on blocked source -> Expect 403 Forbidden
    blocked_analysis = sync_client.post(f"/api/v1/intelligence/analyze/{unverified_id}")
    assert blocked_analysis.status_code == 403
    assert "Eligibility Gate Blocked" in blocked_analysis.json()["error"]["message"]

    # 3. Ingest an authorized own-gameplay source
    eligible_vid = f"yt_eligible_{uid}"
    eligible_payload = {
        "video_id": eligible_vid,
        "title": "Astro Rebel GTA 6 Downtown Heist Run",
        "description": "Clean heist execution with motorcycle getaway",
        "duration_seconds": 380,
        "source_url": f"https://youtube.com/watch?v={eligible_vid}",
        "is_own_gameplay": True,
    }
    resp2 = sync_client.post("/api/v1/discovery/sources", json=eligible_payload)
    assert resp2.status_code == 201
    eligible_id = resp2.json()["id"]

    # 4. Trigger AI analysis on eligible source -> Expect 200 OK with extracted scenes
    analysis_resp = sync_client.post(f"/api/v1/intelligence/analyze/{eligible_id}")
    assert analysis_resp.status_code == 200
    job_data = analysis_resp.json()
    assert job_data["status"] == "completed"
    assert job_data["scene_count"] > 0
    assert len(job_data["scenes"]) > 0
    job_id = job_data["id"]

    # 5. Verify caching: re-triggering without force returns identical job
    cached_resp = sync_client.post(f"/api/v1/intelligence/analyze/{eligible_id}")
    assert cached_resp.status_code == 200
    assert cached_resp.json()["id"] == job_id

    # 6. Retrieve scenes via source endpoint
    scenes_resp = sync_client.get(f"/api/v1/intelligence/sources/{eligible_id}/scenes")
    assert scenes_resp.status_code == 200
    scenes = scenes_resp.json()
    assert len(scenes) == job_data["scene_count"]
    first_scene = scenes[0]
    assert first_scene["start_time"] < first_scene["end_time"]
    assert "scene_label" in first_scene
    assert first_scene["action_intensity"] > 0
