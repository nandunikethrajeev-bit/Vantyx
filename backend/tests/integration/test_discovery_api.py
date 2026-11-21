"""Integration tests for Discovery & Rights API endpoints."""

import uuid
import pytest
from starlette.testclient import TestClient


def test_creator_registration_and_listing(sync_client: TestClient):
    """Verify registering a creator and listing creators."""
    uid = uuid.uuid4().hex[:6]
    creator_payload = {
        "name": f"Rockstar Rebel {uid}",
        "channel_id": f"UC_TEST_REBEL_{uid}",
        "channel_handle": f"@RockstarRebel{uid}",
        "content_category": "GTA 6 Gameplay",
        "is_monitored": True,
        "approval_status": "approved",
        "permission_tier": "authorized_partner",
        "notes": "Contract agreement #8942",
    }
    # 1. Create
    resp = sync_client.post("/api/v1/discovery/creators", json=creator_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == creator_payload["name"]
    assert data["channel_id"] == creator_payload["channel_id"]
    creator_id = data["id"]

    # 2. Duplicate rejection
    dup_resp = sync_client.post("/api/v1/discovery/creators", json=creator_payload)
    assert dup_resp.status_code == 409

    # 3. List
    list_resp = sync_client.get("/api/v1/discovery/creators")
    assert list_resp.status_code == 200
    creators = list_resp.json()
    assert any(c["id"] == creator_id for c in creators)

    # 4. Patch
    patch_resp = sync_client.patch(f"/api/v1/discovery/creators/{creator_id}", json={"notes": "Updated note"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["notes"] == "Updated note"


def test_manual_source_import_and_rights_lifecycle(sync_client: TestClient):
    """Verify ingesting a video source and updating rights records."""
    vid = f"yt_gta6_{uuid.uuid4().hex[:8]}"
    source_payload = {
        "video_id": vid,
        "title": "GTA 6 Extreme Helicopter Chase",
        "description": "Intense escape sequence through Vice City downtown",
        "duration_seconds": 340,
        "source_url": f"https://www.youtube.com/watch?v={vid}",
        "is_own_gameplay": True,
    }
    # 1. Ingest
    resp = sync_client.post("/api/v1/discovery/sources", json=source_payload)
    assert resp.status_code == 201
    source_data = resp.json()
    assert source_data["video_id"] == vid
    assert source_data["is_eligible"] is True
    source_id = source_data["id"]

    # 2. Check eligibility gate
    gate_resp = sync_client.get(f"/api/v1/discovery/sources/{source_id}/eligibility")
    assert gate_resp.status_code == 200
    gate_data = gate_resp.json()
    assert gate_data["is_eligible"] is True
    assert gate_data["permission_status"] == "own_gameplay"

    # 3. Revoke rights and verify gate blocks pipeline
    revoke_payload = {
        "permission_status": "rejected",
        "commercial_use_allowed": False,
    }
    update_resp = sync_client.put(f"/api/v1/discovery/sources/{source_id}/rights", json=revoke_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["permission_status"] == "rejected"

    # 4. Gate must now report NOT eligible
    blocked_resp = sync_client.get(f"/api/v1/discovery/sources/{source_id}/eligibility")
    assert blocked_resp.status_code == 200
    assert blocked_resp.json()["is_eligible"] is False
