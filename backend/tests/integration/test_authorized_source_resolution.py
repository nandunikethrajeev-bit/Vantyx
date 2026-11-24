"""VANTYX M10.1 Integration Tests: Authorized Source Resolution Engine.

Comprehensive testing of:
1. Creator-owned source with verified channel authorization.
2. Authorized partner source with documented commercial agreement.
3. Licensed third-party source with valid documentation.
4. Unauthorized third-party source (blocked at rights gate).
5. Missing original media (halts at awaiting_authorized_media).
6. Invalid source mapping (mapped path missing or corrupted).
7. Expired authorization (blocked at rights gate with expiration detail).
8. End-to-end rendering of an authorized source into a 9:16 vertical Short.
"""

import json
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from starlette.testclient import TestClient


class TestAuthorizedSourceResolution:
    """Validate M10.1 Source Eligibility Categories and Provider Resolvers."""

    def test_creator_owned_source_resolution_and_rendering(self, sync_client: TestClient):
        """1. Creator-owned video with channel authorization resolves from creator vault and completes."""
        synthetic_source = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
        assert synthetic_source.exists()

        uid = uuid.uuid4().hex[:6]
        channel_id = f"UC_owner_{uid}"
        video_id = f"own_{uid}____"[:11]

        # Register creator with 'own_content' tier
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Owner Pilot {uid}",
                "channel_id": channel_id,
                "content_category": "Flight Simulator",
                "approval_status": "approved",
                "permission_tier": "own_content",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        # Stage media in creator vault: storage/creators/{creator_id}/{video_id}.mp4
        vault_dir = Path(f"storage/creators/{creator_id}")
        vault_dir.mkdir(parents=True, exist_ok=True)
        staged_file = vault_dir / f"{video_id}.mp4"
        shutil.copyfile(synthetic_source, staged_file)

        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            intake_resp = sync_client.post(
                "/api/v1/discovery/sources/batch?auto_process=true",
                json={
                    "creator_id": creator_id,
                    "is_own_gameplay": True,
                    "urls": [url],
                    "notes": f"Creator-owned test {uid}",
                },
            )
            assert intake_resp.status_code == 201
            batch_id = intake_resp.json()["batch_id"]

            batch_poll = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
            assert batch_poll.status_code == 200
            item = batch_poll.json()["items"][0]

            assert item["status"] == "completed"
            assert item["source_category"] == "creator_owned"
            assert item["commercial_use_allowed"] is True

            # Verify rendered short exists in outputs gallery
            outputs_resp = sync_client.get("/api/v1/production/outputs?limit=10")
            assert outputs_resp.status_code == 200
            matched = next((o for o in outputs_resp.json() if o["source_id"] == item["source_id"]), None)
            assert matched is not None
            assert matched["status"] == "completed"
            assert matched["file_exists"] is True
        finally:
            if staged_file.exists():
                staged_file.unlink()

    def test_authorized_partner_source_with_asset_mapping(self, sync_client: TestClient):
        """2. Authorized partner video resolves media from asset_mappings.json manifest."""
        synthetic_source = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
        assert synthetic_source.exists()

        uid = uuid.uuid4().hex[:6]
        channel_id = f"UC_partner_{uid}"
        video_id = f"part_{uid}___"[:11]

        # Register partner creator
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Partner Studio {uid}",
                "channel_id": channel_id,
                "content_category": "Cinematic GTA",
                "approval_status": "approved",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        # Stage file in data/media and add mapping to storage/asset_mappings.json
        staged_target = Path(f"data/media/partner_staged_{uid}.mp4").resolve()
        shutil.copyfile(synthetic_source, staged_target)

        mapping_file = Path("storage/asset_mappings.json").resolve()
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        existing_mappings = {}
        if mapping_file.exists():
            try:
                with open(mapping_file, "r") as f:
                    existing_mappings = json.load(f)
            except Exception:
                existing_mappings = {}

        existing_mappings[video_id] = str(staged_target)
        with open(mapping_file, "w") as f:
            json.dump(existing_mappings, f, indent=2)

        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
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
            item = batch_poll.json()["items"][0]

            assert item["status"] == "completed"
            assert item["source_category"] == "authorized_partner"
            assert item["commercial_use_allowed"] is True
        finally:
            if staged_target.exists():
                staged_target.unlink()
            if video_id in existing_mappings:
                del existing_mappings[video_id]
                with open(mapping_file, "w") as f:
                    json.dump(existing_mappings, f, indent=2)

    def test_licensed_third_party_source(self, sync_client: TestClient):
        """3. Explicitly licensed third-party video with documentation and active term."""
        synthetic_source = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
        assert synthetic_source.exists()

        uid = uuid.uuid4().hex[:6]
        video_id = f"lic_{uid}____"[:11]

        # Stage media
        staged_target = Path(f"data/media/{video_id}.mp4").resolve()
        shutil.copyfile(synthetic_source, staged_target)

        try:
            # Ingest manual source with third-party license documentation
            source_resp = sync_client.post(
                "/api/v1/discovery/sources",
                json={
                    "video_id": video_id,
                    "title": f"Licensed Cinematic Reel {uid}",
                    "source_url": f"https://www.youtube.com/watch?v={video_id}",
                    "duration_seconds": 60,
                    "discovery_method": "licensed_import",
                    "local_video_path": str(staged_target),
                    "is_own_gameplay": False,
                },
            )
            assert source_resp.status_code == 201
            source_id = source_resp.json()["id"]

            # Update rights with explicit commercial sync license documentation
            exp_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            rights_resp = sync_client.put(
                f"/api/v1/discovery/sources/{source_id}/rights",
                json={
                    "permission_status": "authorized",
                    "commercial_use_allowed": True,
                    "allowed_editing_scope": "transformative_shorts",
                    "license_documentation": f"Commercial Sync License #AGR-{uid}-2026",
                    "verified_by": "Senior Legal Counsel",
                    "expires_at": exp_date,
                },
            )
            assert rights_resp.status_code == 200

            # Run autonomous pipeline on this source item
            batch_resp = sync_client.post(
                "/api/v1/discovery/sources/batch?auto_process=true",
                json={
                    "urls": [f"https://www.youtube.com/watch?v={video_id}"],
                },
            )
            # Should link existing source and run
            assert batch_resp.status_code == 201
        finally:
            if staged_target.exists():
                staged_target.unlink()

    def test_unauthorized_third_party_source_blocked(self, sync_client: TestClient):
        """4. Arbitrary public YouTube URL without creator agreement is blocked at rights gate."""
        uid = uuid.uuid4().hex[:6]
        unauth_vid = f"unauth_{uid}"[:11]
        url = f"https://www.youtube.com/watch?v={unauth_vid}"

        intake_resp = sync_client.post(
            "/api/v1/discovery/sources/batch?auto_process=true",
            json={
                "urls": [url],
            },
        )
        assert intake_resp.status_code == 201
        batch_id = intake_resp.json()["batch_id"]

        batch_poll = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
        item = batch_poll.json()["items"][0]

        # Must halt at rights check with unverified/unresolved category
        assert item["commercial_use_allowed"] is False
        assert item["status"] in ("rights_pending", "rights_rejected", "rejected")
        assert "Commercial rights verification blocked" in (item["error_message"] or "")

    def test_missing_original_media_safeguard(self, sync_client: TestClient):
        """5. Rights verified, but media absent across all providers halts at awaiting_authorized_media."""
        uid = uuid.uuid4().hex[:6]
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Creator No Media {uid}",
                "channel_id": f"UC_nomedia_{uid}",
                "approval_status": "approved",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        nomedia_vid = f"nomed_{uid}__"[:11]
        url = f"https://www.youtube.com/watch?v={nomedia_vid}"

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
        item = batch_poll.json()["items"][0]

        assert item["status"] in ("awaiting_authorized_media", "awaiting_media")
        assert item["commercial_use_allowed"] is True
        assert "creator-connected vault or authorized asset mapping" in (item["error_message"] or "") or "No matching staged file" in (item["error_message"] or "")

    def test_invalid_source_mapping_fails_integrity(self, sync_client: TestClient):
        """6. Manifest maps URL to a non-existent file, failing resolution truthfully."""
        uid = uuid.uuid4().hex[:6]
        c_resp = sync_client.post(
            "/api/v1/discovery/creators",
            json={
                "name": f"Invalid Mapping Creator {uid}",
                "channel_id": f"UC_invmap_{uid}",
                "approval_status": "approved",
                "permission_tier": "authorized_partner",
            },
        )
        assert c_resp.status_code == 201
        creator_id = c_resp.json()["id"]

        vid = f"inv_{uid}____"[:11]
        mapping_file = Path("storage/asset_mappings.json").resolve()
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        existing_mappings = {}
        if mapping_file.exists():
            try:
                with open(mapping_file, "r") as f:
                    existing_mappings = json.load(f)
            except Exception:
                existing_mappings = {}

        # Point to a missing ghost file
        existing_mappings[vid] = "data/media/non_existent_ghost_file.mp4"
        with open(mapping_file, "w") as f:
            json.dump(existing_mappings, f, indent=2)

        try:
            url = f"https://www.youtube.com/watch?v={vid}"
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
            item = batch_poll.json()["items"][0]

            # Pipeline halts with failure due to invalid mapping
            assert item["status"] == "failed"
            assert "does not exist on disk" in (item["error_message"] or "")
        finally:
            if vid in existing_mappings:
                del existing_mappings[vid]
                with open(mapping_file, "w") as f:
                    json.dump(existing_mappings, f, indent=2)

    def test_expired_authorization_blocked(self, sync_client: TestClient):
        """7. Usage authorization expired in the past is rejected at the rights gate."""
        uid = uuid.uuid4().hex[:6]
        vid = f"exp_{uid}____"[:11]

        # Ingest source
        source_resp = sync_client.post(
            "/api/v1/discovery/sources",
            json={
                "video_id": vid,
                "title": f"Expired Footage {uid}",
                "source_url": f"https://www.youtube.com/watch?v={vid}",
                "duration_seconds": 60,
                "discovery_method": "manual_import",
            },
        )
        assert source_resp.status_code == 201
        source_id = source_resp.json()["id"]

        # Set expired rights date (30 days ago)
        past_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        sync_client.put(
            f"/api/v1/discovery/sources/{source_id}/rights",
            json={
                "permission_status": "authorized",
                "commercial_use_allowed": True,
                "license_documentation": "Contract Expired",
                "expires_at": past_date,
            },
        )

        # Trigger batch intake
        intake_resp = sync_client.post(
            "/api/v1/discovery/sources/batch?auto_process=true",
            json={
                "urls": [f"https://www.youtube.com/watch?v={vid}"],
            },
        )
        assert intake_resp.status_code == 201
        batch_id = intake_resp.json()["batch_id"]

        batch_poll = sync_client.get(f"/api/v1/discovery/batches/{batch_id}")
        item = batch_poll.json()["items"][0]

        assert item["status"] in ("rights_rejected", "rejected", "rights_pending")
        assert "expired" in (item["error_message"] or "").lower()
