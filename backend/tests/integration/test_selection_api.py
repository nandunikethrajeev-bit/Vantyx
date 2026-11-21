"""Integration tests for Intelligent Clip Selection API."""

import uuid
import pytest
from starlette.testclient import TestClient


def test_clip_selection_pipeline(sync_client: TestClient):
    """Verify end-to-end selection generation, ranking, and daily queue."""
    uid = uuid.uuid4().hex[:6]
    vid = f"yt_sel_{uid}"

    # 1. Ingest eligible source
    source_resp = sync_client.post(
        "/api/v1/discovery/sources",
        json={
            "video_id": vid,
            "title": "GTA 6 Downtown Bank Getaway Mission",
            "duration_seconds": 400,
            "source_url": f"https://youtube.com/watch?v={vid}",
            "is_own_gameplay": True,
        },
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    # 2. Trigger AI analysis
    ai_resp = sync_client.post(f"/api/v1/intelligence/analyze/{source_id}")
    assert ai_resp.status_code == 200

    # 3. Generate candidate clips
    gen_resp = sync_client.post(
        f"/api/v1/selection/generate/{source_id}",
        json={"min_score_threshold": 40.0, "max_candidates": 8},
    )
    assert gen_resp.status_code == 200
    candidates = gen_resp.json()
    assert len(candidates) > 0
    first_candidate = candidates[0]
    assert first_candidate["hook_score"] > 0
    assert first_candidate["overall_score"] > 0
    candidate_id = first_candidate["id"]

    # 4. Approve candidate
    patch_resp = sync_client.patch(
        f"/api/v1/selection/candidates/{candidate_id}",
        json={"status": "approved", "title_suggestion": "Viral Escape Masterclass #Shorts"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "approved"
    assert patch_resp.json()["title_suggestion"] == "Viral Escape Masterclass #Shorts"

    # 5. Check daily queue
    queue_resp = sync_client.get("/api/v1/selection/daily-queue?target_count=4")
    assert queue_resp.status_code == 200
    queue_data = queue_resp.json()
    assert queue_data["target_count"] == 4
    assert len(queue_data["candidates"]) > 0
