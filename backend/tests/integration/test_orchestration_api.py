"""Integration tests for VANTYX Orchestration & Autonomous Control API."""

import uuid
from starlette.testclient import TestClient


def test_automation_status_and_config(sync_client: TestClient):
    """Verify status endpoint and runtime configuration update."""
    # 1. Fetch status
    status_resp = sync_client.get("/api/v1/orchestration/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "automation_enabled" in status_data
    assert "daily_run_time_ist" in status_data
    assert "celery_mode" in status_data
    assert status_data["timezone"] == "Asia/Kolkata"
    assert status_data["disk_free_gb"] >= 0.0

    # 2. Update configuration (enable automation)
    patch_resp = sync_client.patch(
        "/api/v1/orchestration/config",
        json={"automation_enabled": True, "daily_run_time_ist": "07:30"},
    )
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["automation_enabled"] is True
    assert updated_data["daily_run_time_ist"] == "07:30"


def test_daily_publishing_plan_endpoint(sync_client: TestClient):
    """Verify daily plan endpoint returns 4 slots for Asia/Kolkata."""
    plan_date = "2027-03-01"
    resp = sync_client.get(f"/api/v1/orchestration/plan?target_date={plan_date}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_date"] == plan_date
    assert data["target_count"] == 4
    assert data["timezone"] == "Asia/Kolkata"

    slots = data["slot_assignments"]
    assert "09:00" in slots
    assert "13:00" in slots
    assert "17:00" in slots
    assert "21:00" in slots


def test_end_to_end_autonomous_workflow_pipeline(sync_client: TestClient):
    """Test full 7-step autonomous workflow execution end-to-end."""
    uid = uuid.uuid4().hex[:6]
    unique_day = (int(uid, 16) % 25) + 1
    target_date = f"2027-04-{unique_day:02d}"

    # 1. Seed an authorized creator and source to allow full pipeline completion
    creator_resp = sync_client.post(
        "/api/v1/discovery/creators",
        json={
            "name": f"Astro Rebel Partner {uid}",
            "channel_id": f"UC_orch_test_{uid}",
            "content_category": "GTA 6 Gameplay",
            "is_monitored": True,
            "approval_status": "approved",
            "permission_tier": "authorized_partner",
        },
    )
    assert creator_resp.status_code == 201

    source_resp = sync_client.post(
        "/api/v1/discovery/sources",
        json={
            "video_id": f"orch_vid_{uid}",
            "title": "GTA 6 Autonomous Test Heist",
            "duration_seconds": 220,
            "source_url": f"https://youtube.com/watch?v=orch_{uid}",
            "is_own_gameplay": True,
        },
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    # 2. Trigger workflow run synchronously
    wf_resp = sync_client.post(
        "/api/v1/orchestration/start",
        json={
            "target_date": target_date,
            "force": True,
            "execute_sync": True,
        },
    )
    assert wf_resp.status_code == 201
    wf_data = wf_resp.json()
    run_id = wf_data["run_id"]

    assert wf_data["status"] == "completed"
    assert wf_data["current_step"] == "completed"
    assert len(wf_data["steps"]) == 7

    # Verify each step completed
    for step in wf_data["steps"]:
        assert step["status"] == "completed", f"Step {step['step_name']} did not complete"

    # Verify steps names
    step_names = [s["step_name"] for s in wf_data["steps"]]
    assert step_names == [
        "discovery",
        "rights_validation",
        "intelligence",
        "selection",
        "production",
        "distribution",
        "monitoring",
    ]

    # Verify execution metadata
    metadata = wf_data.get("execution_metadata", {})
    assert metadata.get("sources_discovered", 0) >= 0
    assert metadata.get("eligible_sources", 0) >= 1
    assert metadata.get("scenes_indexed", 0) >= 1
    assert metadata.get("candidates_selected", 0) >= 1

    # 3. Verify workflow is retrievable via GET
    get_resp = sync_client.get(f"/api/v1/orchestration/workflows/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id

    # 4. Verify plan was updated
    plan_resp = sync_client.get(f"/api/v1/orchestration/plan?target_date={target_date}")
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["plan_date"] == target_date
    assert plan_data["filled_count"] >= 0


def test_workflow_pause_and_cancel_endpoints(sync_client: TestClient):
    """Verify pause and cancel REST endpoints."""
    uid = uuid.uuid4().hex[:6]
    unique_day = (int(uid, 16) % 25) + 1
    target_date = f"2027-05-{unique_day:02d}"

    # Start async/non-executing workflow
    start_resp = sync_client.post(
        "/api/v1/orchestration/start",
        json={"target_date": target_date, "force": True, "execute_sync": False},
    )
    assert start_resp.status_code == 201
    run_id = start_resp.json()["run_id"]

    # Pause
    pause_resp = sync_client.post(f"/api/v1/orchestration/workflows/{run_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    # Cancel
    cancel_resp = sync_client.post(f"/api/v1/orchestration/workflows/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
