"""Integration tests for Video Production API and vertical Short synthesis."""

import os
import uuid
import pytest
from starlette.testclient import TestClient


def test_video_render_pipeline_and_streaming(sync_client: TestClient):
    """Verify end-to-end rendering from candidate clip to completed 9:16 vertical video."""
    uid = uuid.uuid4().hex[:6]
    vid = f"yt_prod_{uid}"

    # 1. Ingest eligible source
    source_resp = sync_client.post(
        "/api/v1/discovery/sources",
        json={
            "video_id": vid,
            "title": "GTA 6 High Velocity Police Stunt Jump",
            "duration_seconds": 300,
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
        json={"min_score_threshold": 40.0, "max_candidates": 4},
    )
    assert gen_resp.status_code == 200
    candidates = gen_resp.json()
    assert len(candidates) > 0
    candidate_id = candidates[0]["id"]

    # 4. Trigger video render job
    render_resp = sync_client.post(
        f"/api/v1/production/render/{candidate_id}",
        json={
            "layout_style": "blurred_backdrop",
            "has_burned_subtitles": True,
            "resolution": "1080x1920",
            "normalize_audio": True,
        },
    )
    assert render_resp.status_code == 200
    job = render_resp.json()
    assert job["candidate_id"] == candidate_id
    assert job["status"] == "completed"
    assert job["progress_pct"] == 100.0
    assert job["output_file_path"] is not None
    assert os.path.exists(job["output_file_path"])
    assert os.path.getsize(job["output_file_path"]) > 1000

    job_id = job["id"]

    # 5. List jobs
    jobs_list_resp = sync_client.get("/api/v1/production/jobs")
    assert jobs_list_resp.status_code == 200
    job_ids = [j["id"] for j in jobs_list_resp.json()]
    assert job_id in job_ids

    # 6. Stream video endpoint
    stream_resp = sync_client.get(f"/api/v1/production/jobs/{job_id}/stream")
    assert stream_resp.status_code == 200
    assert stream_resp.headers["content-type"] == "video/mp4"
    assert len(stream_resp.content) > 1000
