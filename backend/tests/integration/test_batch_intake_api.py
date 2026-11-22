"""Integration tests for Batch URL Intake, URL Normalization, and Rights Safeguards."""

import uuid
import pytest
from starlette.testclient import TestClient


class TestBatchIntakeApi:
    """Comprehensive test suite for POST /api/v1/discovery/sources/batch and batch tracking."""

    # 1. Successful Batch Intake with Approved Partner Creator
    def test_batch_intake_with_approved_creator_partner(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        # Register approved partner creator
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Astro Rebel Partner {uid}",
                "channel_id": f"UC_batch_partner_{uid}",
                "content_category": "GTA 6 Gameplay",
                "approval_status": "approved",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        vid1 = f"v1_{uid}____"[:11]
        vid2 = f"v2_{uid}____"[:11]
        payload = {
            "creator_id": creator_id,
            "urls": [
                f"https://www.youtube.com/watch?v={vid1}",
                f"https://youtu.be/{vid2}?si=test_tracking",
            ],
            "notes": "Morning authorized batch submission",
        }

        resp = sync_client.post("/api/v1/discovery/sources/batch", json=payload)
        assert resp.status_code == 201
        data = resp.json()

        assert data["batch_id"].startswith("batch_")
        assert data["creator_id"] == creator_id
        assert data["total_submitted"] == 2
        assert data["total_valid"] == 2
        assert data["total_duplicates"] == 0
        assert data["total_rejected"] == 0
        assert data["status"] == "completed"
        assert len(data["items"]) == 2

        # Check item details & rights corroboration
        item1 = data["items"][0]
        assert item1["video_id"] == vid1
        assert item1["canonical_url"] == f"https://www.youtube.com/watch?v={vid1}"
        assert item1["status"] == "eligible"
        assert item1["is_eligible"] is True
        assert item1["permission_status"] == "authorized"
        assert item1["commercial_use_allowed"] is True
        assert item1["source_id"] is not None

        item2 = data["items"][1]
        assert item2["video_id"] == vid2
        assert item2["canonical_url"] == f"https://www.youtube.com/watch?v={vid2}"
        assert item2["status"] == "eligible"
        assert item2["is_eligible"] is True

    # 2. Approved Creator with Own Content Tier
    def test_batch_intake_with_approved_creator_own_content(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Astro Rebel Core Studio {uid}",
                "channel_id": f"UC_batch_own_{uid}",
                "approval_status": "approved",
                "permission_tier": "own_content",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        vid = f"own_{uid}_vid"[:11]
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={
                "creator_id": creator_id,
                "is_own_gameplay": True,
                "urls": [f"https://www.youtube.com/shorts/{vid}"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_valid"] == 1
        item = data["items"][0]
        assert item["status"] == "eligible"
        assert item["is_eligible"] is True
        assert item["permission_status"] == "own_gameplay"
        assert item["commercial_use_allowed"] is True

    # 3. Unverified Caller Claim (No Approved Creator -> pending_verification)
    def test_batch_intake_unverified_claim_fails_safe(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        vid = f"unv_{uid}_vid"[:11]
        # Caller claims is_own_gameplay=True but provides no verified creator record
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={
                "creator_id": None,
                "is_own_gameplay": True,
                "urls": [f"https://www.youtube.com/watch?v={vid}"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_valid"] == 1
        item = data["items"][0]
        # Strict Fail-Safe: Must be marked pending_verification and ineligible
        assert item["status"] == "pending_verification"
        assert item["is_eligible"] is False
        assert item["permission_status"] == "pending"
        assert item["commercial_use_allowed"] is False

    # 4. Non-Existent Creator Reference
    def test_batch_intake_non_existent_creator(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        vid = f"noc_{uid}_vid"[:11]
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={
                "creator_id": 999999,
                "urls": [f"https://www.youtube.com/watch?v={vid}"],
            },
        )
        assert resp.status_code == 201
        item = resp.json()["items"][0]
        assert item["status"] == "pending_verification"
        assert item["is_eligible"] is False
        assert item["permission_status"] == "pending"

    # 5. Creator with Pending/Rejected Approval Status
    def test_batch_intake_unapproved_creator(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Pending Creator {uid}",
                "channel_id": f"UC_pending_{uid}",
                "approval_status": "pending",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        vid = f"pnd_{uid}_vid"[:11]
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={
                "creator_id": creator_id,
                "urls": [f"https://www.youtube.com/watch?v={vid}"],
            },
        )
        assert resp.status_code == 201
        item = resp.json()["items"][0]
        assert item["status"] == "pending_verification"
        assert item["is_eligible"] is False

    # 6. In-Batch Duplicates Handling
    def test_batch_intake_in_batch_duplicates(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        vid_a = f"da_{uid}____"[:11]
        vid_b = f"db_{uid}____"[:11]
        urls = [
            f"https://www.youtube.com/watch?v={vid_a}",
            f"https://youtu.be/{vid_b}",
            f"https://youtu.be/{vid_a}?si=tracking",  # duplicate of vid_a
            f"https://www.youtube.com/shorts/{vid_b}",  # duplicate of vid_b
        ]

        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={"urls": urls},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_submitted"] == 4
        assert data["total_valid"] == 2
        assert data["total_duplicates"] == 2
        assert data["total_rejected"] == 0
        assert data["status"] == "partially_completed"

        items = data["items"]
        assert items[0]["status"] == "pending_verification"
        assert items[1]["status"] == "pending_verification"
        assert items[2]["status"] == "duplicate"
        assert "Duplicate video ID" in items[2]["error_message"]
        assert items[3]["status"] == "duplicate"
        assert "Duplicate video ID" in items[3]["error_message"]

    # 7. Already Registered Catalog Source Duplicate
    def test_batch_intake_already_registered_catalog_duplicate(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        vid_existing = f"ex_{uid}____"[:11]
        vid_new = f"nw_{uid}____"[:11]

        # 1. Pre-register vid_existing
        pre_resp = sync_client.post(
            "/api/v1/discovery/sources",
            json={
                "video_id": vid_existing,
                "title": "Pre-existing video",
                "source_url": f"https://www.youtube.com/watch?v={vid_existing}",
            },
        )
        assert pre_resp.status_code == 201
        pre_source_id = pre_resp.json()["id"]

        # 2. Submit batch with both existing and new
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={
                "urls": [
                    f"https://youtu.be/{vid_existing}",
                    f"https://www.youtube.com/watch?v={vid_new}",
                ]
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_submitted"] == 2
        assert data["total_valid"] == 1
        assert data["total_duplicates"] == 1

        dup_item = data["items"][0]
        assert dup_item["status"] == "duplicate"
        assert dup_item["source_id"] == pre_source_id
        assert "already registered" in dup_item["error_message"]

        new_item = data["items"][1]
        assert new_item["status"] == "pending_verification"
        assert new_item["video_id"] == vid_new

    # 8. Partial Success with Invalid and Malformed URLs
    def test_batch_intake_partial_success(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        vid1 = f"p1_{uid}____"[:11]
        vid2 = f"p2_{uid}____"[:11]

        urls = [
            f"https://www.youtube.com/watch?v={vid1}",
            "https://vimeo.com/123456789",  # Unsupported host
            f"https://www.youtube.com/shorts/{vid2}",
            "not_a_valid_url_at_all",  # Malformed
            "https://www.youtube.com/watch?v=short",  # Invalid ID length
        ]

        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={"urls": urls},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_submitted"] == 5
        assert data["total_valid"] == 2
        assert data["total_rejected"] == 3
        assert data["status"] == "partially_completed"

        items = data["items"]
        assert items[0]["status"] == "pending_verification"
        assert items[1]["status"] == "rejected"
        assert "Unsupported host" in items[1]["error_message"]
        assert items[2]["status"] == "pending_verification"
        assert items[3]["status"] == "rejected"
        assert items[4]["status"] == "rejected"

    # 9. Empty Batch Validation
    def test_batch_intake_empty_batch_rejected(self, sync_client: TestClient):
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={"urls": []},
        )
        assert resp.status_code == 422

    # 10. Batch Exceeding 20 URLs
    def test_batch_intake_exceeding_20_urls_rejected(self, sync_client: TestClient):
        excessive_urls = [f"https://www.youtube.com/watch?v=vid_{i:07d}" for i in range(21)]
        resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={"urls": excessive_urls},
        )
        assert resp.status_code == 422

    # 11. Batch Retrieval via GET
    def test_get_batch_details_and_list_batches(self, sync_client: TestClient):
        uid = uuid.uuid4().hex[:6]
        vid = f"get_{uid}_01"[:11]
        post_resp = sync_client.post(
            "/api/v1/discovery/sources/batch",
            json={"urls": [f"https://www.youtube.com/watch?v={vid}"]},
        )
        assert post_resp.status_code == 201
        batch_id = post_resp.json()["batch_id"]

        # GET /discovery/batches/{batch_id}
        get_resp = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["batch_id"] == batch_id
        assert len(get_data["items"]) == 1

        # GET /discovery/batches (list)
        list_resp = sync_client.get("/api/v1/discovery/batches?limit=10")
        assert list_resp.status_code == 200
        batches = list_resp.json()
        assert len(batches) >= 1
        assert any(b["batch_id"] == batch_id for b in batches)

    # 12. Non-existent batch 404
    def test_get_non_existent_batch_404(self, sync_client: TestClient):
        resp = sync_client.get("/api/v1/discovery/batches/batch_non_existent_123456")
        assert resp.status_code == 404
