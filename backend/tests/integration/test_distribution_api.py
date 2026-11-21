"""Integration tests for Distribution API, OAuth endpoints, scheduling calendar, and publishing."""

import os
import uuid
import pytest
from starlette.testclient import TestClient


def test_oauth_endpoints(sync_client: TestClient):
    """Verify OAuth URL retrieval and channel status endpoints."""
    url_resp = sync_client.get("/api/v1/distribution/oauth/url")
    assert url_resp.status_code == 200
    data = url_resp.json()
    assert "configured" in data

    status_resp = sync_client.get("/api/v1/distribution/oauth/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "authorized" in status_data


def test_daily_slots_endpoint(sync_client: TestClient):
    """Verify daily 4-slots calendar retrieval in Asia/Kolkata."""
    resp = sync_client.get("/api/v1/distribution/schedule/slots?date=2026-12-25")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_date"] == "2026-12-25"
    assert data["timezone"] == "Asia/Kolkata"
    assert len(data["slots"]) == 4

    slot_names = [s["slot_name"] for s in data["slots"]]
    assert slot_names == ["09:00", "13:00", "17:00", "21:00"]


def test_synthetic_media_rejection_at_publishing_gate(sync_client: TestClient):
    """Verify that synthetic test media is strictly blocked from the publishing queue."""
    uid = uuid.uuid4().hex[:6]
    vid = f"yt_synth_{uid}"

    # 1. Ingest source
    source_resp = sync_client.post(
        "/api/v1/discovery/sources",
        json={
            "video_id": vid,
            "title": "GTA 6 Synthetic Test Demo",
            "duration_seconds": 300,
            "source_url": f"https://youtube.com/watch?v={vid}",
            "is_own_gameplay": True,
        },
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    # 2. Analyze & Generate Candidate
    sync_client.post(f"/api/v1/intelligence/analyze/{source_id}")
    gen_resp = sync_client.post(
        f"/api/v1/selection/generate/{source_id}",
        json={"min_score_threshold": 30.0, "max_candidates": 2},
    )
    candidates = gen_resp.json()
    assert len(candidates) > 0
    candidate_id = candidates[0]["id"]

    # 3. Render (since no local video file exists, this generates synthetic fallback marked is_synthetic=True)
    render_resp = sync_client.post(f"/api/v1/production/render/{candidate_id}")
    assert render_resp.status_code == 200
    job = render_resp.json()
    assert job["is_synthetic"] is True
    job_id = job["id"]

    # 4. Attempt to schedule synthetic media -> Must be rejected with 400
    schedule_resp = sync_client.post(
        "/api/v1/distribution/schedule",
        json={
            "candidate_id": candidate_id,
            "render_job_id": job_id,
            "target_date": "2026-12-25",
            "slot_name": "09:00",
        },
    )
    assert schedule_resp.status_code == 400
    err_text = schedule_resp.json().get("error", {}).get("message") or schedule_resp.json().get("detail", "")
    assert "Synthetic test media is strictly prohibited" in err_text


def test_scheduling_and_publishing_workflow(sync_client: TestClient, tmp_path):
    """Verify scheduling an authorized real video, duplicate prevention, and mock publishing."""
    uid = uuid.uuid4().hex[:6]
    vid = f"yt_dist_{uid}"

    # Create dummy genuine video file
    dummy_video_file = tmp_path / f"real_gameplay_{uid}.mp4"
    dummy_video_file.write_bytes(b"VALID_MP4_BINARY_DATA" * 100)

    # 1. Ingest source with real local path
    source_resp = sync_client.post(
        "/api/v1/discovery/sources",
        json={
            "video_id": vid,
            "title": "GTA 6 Genuine Heist Playthrough",
            "duration_seconds": 250,
            "source_url": f"https://youtube.com/watch?v={vid}",
            "is_own_gameplay": True,
        },
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    # 2. Analyze & Generate Candidate
    sync_client.post(f"/api/v1/intelligence/analyze/{source_id}")
    gen_resp = sync_client.post(
        f"/api/v1/selection/generate/{source_id}",
        json={"min_score_threshold": 30.0, "max_candidates": 2},
    )
    candidates = gen_resp.json()
    assert len(candidates) > 0
    candidate_id = candidates[0]["id"]

    # 3. Simulate completed real render job
    render_resp = sync_client.post(f"/api/v1/production/render/{candidate_id}")
    assert render_resp.status_code == 200
    job = render_resp.json()
    job_id = job["id"]

    # Temporarily clear is_synthetic in DB for this test to simulate real video pipeline
    from app.db.session import get_sync_engine
    from sqlalchemy import text
    with get_sync_engine().begin() as conn:
        conn.execute(text(f"UPDATE render_jobs SET is_synthetic = 0 WHERE id = {job_id}"))

    # 4. Schedule for future slot
    unique_day = (int(uid, 16) % 25) + 1
    target_date = f"2027-01-{unique_day:02d}"
    sched_resp = sync_client.post(
        "/api/v1/distribution/schedule",
        json={
            "candidate_id": candidate_id,
            "render_job_id": job_id,
            "target_date": target_date,
            "slot_name": "13:00",
            "title": "GTA 6 Epic Bank Escape #Shorts",
        },
    )
    assert sched_resp.status_code == 201
    schedule = sched_resp.json()
    assert schedule["slot_name"] == "13:00"
    assert schedule["status"] == "scheduled"
    assert schedule["target_channel"] == "Astro Rebel"
    schedule_id = schedule["id"]

    # 5. Prevent duplicate scheduling of the same candidate
    dup_resp = sync_client.post(
        "/api/v1/distribution/schedule",
        json={
            "candidate_id": candidate_id,
            "render_job_id": job_id,
            "target_date": target_date,
            "slot_name": "17:00",
        },
    )
    assert dup_resp.status_code == 400
    dup_err_text = dup_resp.json().get("error", {}).get("message") or dup_resp.json().get("detail", "")
    assert "already scheduled" in dup_err_text

    # 6. Execute Mock Publish
    pub_resp = sync_client.post(f"/api/v1/distribution/publish/{schedule_id}?force_mock=true")
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert pub_data["status"] == "published"
    assert pub_data["is_mock"] is True
    assert pub_data["youtube_video_id"].startswith("mock_yt_")
    assert "https://youtube.com/shorts/" in pub_data["publish_url"]
