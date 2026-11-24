"""VANTYX M10.2: Real-World Source Resolution Acceptance Script.

Executes the complete real-world acceptance workflow:
1. Register creator with verified channel ownership.
2. Place original master video in creator-connected vault: storage/creators/{creator_id}/{video_id}.mp4.
3. Submit YouTube URL through batch intake with auto_process=True.
4. Verify metadata retrieval, rights evaluation (creator_owned), and media resolution.
5. Verify FFprobe integrity validation.
6. Verify automated pipeline execution (analysis, candidate ranking, 9:16 Short render).
7. Inspect rendered MP4 with FFprobe (1080x1920, H.264/AAC, duration, file size).
8. Verify HTTP 206 Partial Content range streaming and HTTP 200 attachment download.
9. Verify all 5 failure scenarios:
   - Unauthorized third-party URL blocked.
   - Creator without verified ownership blocked.
   - Missing media halts at awaiting_authorized_media.
   - Expired license blocked.
   - Corrupt master file fails safely.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from starlette.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def run_ffprobe(file_path: Path) -> dict:
    ffmpeg_exe = settings.get_ffmpeg_executable()
    ffprobe_exe = str(Path(ffmpeg_exe).parent / "ffprobe.exe")
    has_ffprobe = os.path.exists(ffprobe_exe) or shutil.which("ffprobe") is not None
    if not os.path.exists(ffprobe_exe) and shutil.which("ffprobe"):
        ffprobe_exe = shutil.which("ffprobe")

    if has_ffprobe:
        cmd = [
            ffprobe_exe,
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json",
            str(file_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    else:
        # Probe using FFmpeg directly
        cmd = [ffmpeg_exe, "-i", str(file_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        out = res.stderr or ""
        duration = 0.0
        dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out)
        if dur_m:
            duration = int(dur_m.group(1)) * 3600 + int(dur_m.group(2)) * 60 + float(dur_m.group(3))

        streams = []
        vid_m = re.search(r"Stream #\d+:\d+.*Video:\s*(\w+).*?(\d{3,4})x(\d{3,4})", out)
        if vid_m:
            streams.append({
                "codec_type": "video",
                "codec_name": vid_m.group(1),
                "width": int(vid_m.group(2)),
                "height": int(vid_m.group(3)),
            })
        aud_m = re.search(r"Stream #\d+:\d+.*Audio:\s*(\w+)", out)
        if aud_m:
            streams.append({
                "codec_type": "audio",
                "codec_name": aud_m.group(1),
            })
        return {
            "format": {
                "duration": duration,
                "size": file_path.stat().st_size,
            },
            "streams": streams,
        }


def main():
    print("=" * 80)
    print("VANTYX M10.2 — REAL-WORLD SOURCE RESOLUTION ACCEPTANCE SUITE")
    print("=" * 80)

    # Master video source
    master_footage = Path("data/media/synthetic_test_footage_1080p.mp4").resolve()
    assert master_footage.exists(), f"Master footage missing at {master_footage}"
    print(f"[*] Found master footage asset: {master_footage.name} ({master_footage.stat().st_size} bytes)")

    # --------------------------------------------------------------------------
    # 1. Creator Registration & Ownership Verification
    # --------------------------------------------------------------------------
    uid = uuid.uuid4().hex[:6]
    channel_id = f"UC_AstroRebel_{uid}"
    video_id = f"ast_{uid}____"[:11]
    creator_name = f"Astro Rebel Aviation {uid}"

    print(f"\n[Step 1] Registering creator '{creator_name}' with verified channel ownership...")
    c_resp = client.post(
        "/api/v1/discovery/creators",
        json={
            "name": creator_name,
            "channel_id": channel_id,
            "channel_handle": f"@AstroRebel_{uid}",
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "content_category": "Flight Simulation",
            "approval_status": "approved",
            "permission_tier": "own_content",
            "notes": "Verified partner channel ownership via bilateral content agreement",
        },
    )
    assert c_resp.status_code == 201, f"Failed to register creator: {c_resp.text}"
    creator = c_resp.json()
    creator_id = creator["id"]
    print(f" -> Creator #{creator_id} registered successfully (Approval: {creator['approval_status']}, Tier: {creator['permission_tier']})")

    # --------------------------------------------------------------------------
    # 2. Place Original Master Video in Creator-Connected Vault
    # --------------------------------------------------------------------------
    vault_dir = Path(f"storage/creators/{creator_id}").resolve()
    vault_dir.mkdir(parents=True, exist_ok=True)
    vault_file = vault_dir / f"{video_id}.mp4"
    shutil.copyfile(master_footage, vault_file)
    print(f"\n[Step 2] Staged master video in creator vault:")
    print(f" -> Vault Path: storage/creators/{creator_id}/{vault_file.name} ({vault_file.stat().st_size} bytes)")

    try:
        # ----------------------------------------------------------------------
        # 3. Submit YouTube URL through URL Studio Batch Intake
        # ----------------------------------------------------------------------
        source_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"\n[Step 3] Submitting YouTube URL: {source_url} with auto_process=True...")
        intake_resp = client.post(
            "/api/v1/discovery/sources/batch?auto_process=true",
            json={
                "creator_id": creator_id,
                "is_own_gameplay": True,
                "urls": [source_url],
                "notes": f"Acceptance test run {uid}",
            },
        )
        assert intake_resp.status_code == 201, f"Batch intake failed: {intake_resp.text}"
        batch = intake_resp.json()
        batch_id = batch["batch_id"]
        print(f" -> Batch {batch_id} accepted. Processing pipeline executed.")

        # ----------------------------------------------------------------------
        # 4. Confirm Pipeline State Transitions & Acceptance
        # ----------------------------------------------------------------------
        batch_poll = client.get(f"/api/v1/discovery/batches/{batch_id}")
        assert batch_poll.status_code == 200
        items = batch_poll.json()["items"]
        assert len(items) == 1
        item = items[0]

        print(f"\n[Step 4] Pipeline Results for {video_id}:")
        print(f" -> Status: {item['status']}")
        print(f" -> Category: {item.get('source_category')}")
        print(f" -> Commercial Use Allowed: {item['commercial_use_allowed']}")
        print(f" -> Source Title: {item.get('source_title')}")
        print(f" -> Creator Name: {item.get('creator_name')}")

        assert item["status"] == "completed", f"Expected completed status, got {item['status']}: {item.get('error_message')}"
        assert item["source_category"] == "creator_owned"
        assert item["commercial_use_allowed"] is True

        source_id = item["source_id"]

        # ----------------------------------------------------------------------
        # 5. Confirm Scenes & Moments Generated
        # ----------------------------------------------------------------------
        scenes_resp = client.get(f"/api/v1/intelligence/sources/{source_id}/scenes")
        assert scenes_resp.status_code == 200
        scenes = scenes_resp.json()
        print(f"\n[Step 5] Video Intelligence:")
        print(f" -> Extracted Scenes: {len(scenes)} scenes detected via native FFmpeg cuts")

        candidates_resp = client.get(f"/api/v1/selection/candidates?source_id={source_id}")
        assert candidates_resp.status_code == 200
        candidates = candidates_resp.json()
        print(f" -> Candidate Moments: {len(candidates)} ranked moments")
        top_cand = candidates[0]
        print(f" -> Top Moment: '{top_cand['title_suggestion']}' ({top_cand['duration_seconds']}s, PTS: {top_cand['overall_score']})")

        # ----------------------------------------------------------------------
        # 6. Verify Output Gallery & Rendered MP4
        # ----------------------------------------------------------------------
        outputs_resp = client.get("/api/v1/production/outputs?limit=10")
        assert outputs_resp.status_code == 200
        outputs = outputs_resp.json()
        matched = next((o for o in outputs if o["source_id"] == source_id), None)
        assert matched is not None, "Rendered Short missing from outputs gallery"
        assert matched["file_exists"] is True

        rendered_path = Path(matched["output_file_path"])
        if not rendered_path.is_absolute():
            rendered_path = (backend_dir.parent / rendered_path).resolve()
        assert rendered_path.exists(), f"Rendered MP4 file missing at {rendered_path}"
        file_size_bytes = rendered_path.stat().st_size
        print(f"\n[Step 6] Rendered Output Short:")
        print(f" -> Output Path: {rendered_path.name}")
        print(f" -> File Size: {file_size_bytes} bytes ({round(file_size_bytes / (1024*1024), 2)} MB)")
        assert file_size_bytes > 100_000, "Rendered MP4 file is truncated"

        # ----------------------------------------------------------------------
        # 7. FFprobe Probe on Rendered Short
        # ----------------------------------------------------------------------
        probe_info = run_ffprobe(rendered_path)
        streams = probe_info.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        assert v_stream is not None, "Rendered video has no video stream"
        assert a_stream is not None, "Rendered video has no audio stream"
        width = int(v_stream.get("width", 0))
        height = int(v_stream.get("height", 0))
        v_codec = v_stream.get("codec_name", "")
        a_codec = a_stream.get("codec_name", "")
        duration = float(probe_info.get("format", {}).get("duration", 0.0))

        print(f"\n[Step 7] FFprobe Stream Validation:")
        print(f" -> Resolution: {width}x{height} (Aspect: 9:16 Vertical HD)")
        print(f" -> Video Codec: {v_codec}")
        print(f" -> Audio Codec: {a_codec}")
        print(f" -> Duration: {duration:.2f}s")

        assert width == 1080 and height == 1920, f"Expected 1080x1920, got {width}x{height}"
        assert v_codec == "h264", f"Expected h264, got {v_codec}"
        assert a_codec == "aac", f"Expected aac, got {a_codec}"

        # ----------------------------------------------------------------------
        # 8. Browser Playback Stream (HTTP 206 Partial Content)
        # ----------------------------------------------------------------------
        job_id = matched["job_id"]
        print(f"\n[Step 8] Testing Browser Playback (Job #{job_id}):")
        # Full stream request
        stream_resp = client.get(f"/api/v1/production/jobs/{job_id}/stream")
        assert stream_resp.status_code in (200, 206)
        assert "bytes" in stream_resp.headers.get("accept-ranges", "").lower()
        print(f" -> GET /stream: HTTP {stream_resp.status_code} (Accept-Ranges: {stream_resp.headers.get('accept-ranges')})")

        # Range request (e.g. Chrome video player range query)
        range_resp = client.get(
            f"/api/v1/production/jobs/{job_id}/stream",
            headers={"Range": "bytes=0-1024"},
        )
        assert range_resp.status_code == 206, f"Expected 206 Partial Content, got {range_resp.status_code}"
        assert "content-range" in range_resp.headers
        assert len(range_resp.content) == 1025
        print(f" -> Range Request: HTTP 206 Partial Content (Content-Range: {range_resp.headers['content-range']})")

        # ----------------------------------------------------------------------
        # 9. Direct MP4 Download Endpoint
        # ----------------------------------------------------------------------
        print(f"\n[Step 9] Testing MP4 Download Endpoint:")
        download_resp = client.get(f"/api/v1/production/jobs/{job_id}/download")
        assert download_resp.status_code == 200
        assert "attachment" in download_resp.headers.get("content-disposition", "")
        assert len(download_resp.content) == file_size_bytes
        print(f" -> GET /download: HTTP 200 OK (Content-Disposition: {download_resp.headers.get('content-disposition')})")
        print(f" -> Download payload: {len(download_resp.content)} bytes received")

    finally:
        if vault_file.exists():
            vault_file.unlink()

    # --------------------------------------------------------------------------
    # 10. Additional Failure Tests (5 Failure Scenarios)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VERIFYING 5 FAILURE SAFEGUARDS")
    print("=" * 80)

    # Failure Test 1: Unauthorized Third-Party URL
    unauth_vid = f"unauth_{uid}"[:11]
    print(f"\n[Failure 1] Submitting arbitrary third-party URL: https://youtube.com/watch?v={unauth_vid}...")
    f1_resp = client.post("/api/v1/discovery/sources/batch?auto_process=true", json={"urls": [f"https://www.youtube.com/watch?v={unauth_vid}"]})
    assert f1_resp.status_code == 201
    f1_item = client.get(f"/api/v1/discovery/batches/{f1_resp.json()['batch_id']}").json()["items"][0]
    print(f" -> Status: {f1_item['status']}")
    print(f" -> Diagnostic: {f1_item['error_message']}")
    assert f1_item["status"] in ("rights_pending", "rights_rejected", "rejected")
    assert f1_item["commercial_use_allowed"] is False
    print(" -> PASS: Arbitrary third-party URL blocked at rights gate.")

    # Failure Test 2: Creator without verified ownership
    unver_c_resp = client.post(
        "/api/v1/discovery/creators",
        json={
            "name": f"Unverified Gamer {uid}",
            "channel_id": f"UC_unverified_{uid}",
            "approval_status": "pending",
            "permission_tier": "unverified",
        },
    )
    unver_cid = unver_c_resp.json()["id"]
    unver_vid = f"unver_{uid}"[:11]
    print(f"\n[Failure 2] Submitting URL for unverified creator #{unver_cid}...")
    f2_resp = client.post("/api/v1/discovery/sources/batch?auto_process=true", json={"creator_id": unver_cid, "urls": [f"https://www.youtube.com/watch?v={unver_vid}"]})
    f2_item = client.get(f"/api/v1/discovery/batches/{f2_resp.json()['batch_id']}").json()["items"][0]
    print(f" -> Status: {f2_item['status']}")
    print(f" -> Diagnostic: {f2_item['error_message']}")
    assert f2_item["status"] in ("rights_pending", "rights_rejected", "rejected")
    print(" -> PASS: Creator without verified ownership blocked at rights gate.")

    # Failure Test 3: Missing media halts at awaiting_authorized_media
    partner_c_resp = client.post(
        "/api/v1/discovery/creators",
        json={
            "name": f"Partner No Media {uid}",
            "channel_id": f"UC_nomedia_{uid}",
            "approval_status": "approved",
            "permission_tier": "authorized_partner",
        },
    )
    partner_cid = partner_c_resp.json()["id"]
    nomedia_vid = f"nomed_{uid}"[:11]
    print(f"\n[Failure 3] Approved partner source without media on disk: {nomedia_vid}...")
    f3_resp = client.post("/api/v1/discovery/sources/batch?auto_process=true", json={"creator_id": partner_cid, "urls": [f"https://www.youtube.com/watch?v={nomedia_vid}"]})
    f3_item = client.get(f"/api/v1/discovery/batches/{f3_resp.json()['batch_id']}").json()["items"][0]
    print(f" -> Status: {f3_item['status']}")
    print(f" -> Diagnostic: {f3_item['error_message']}")
    assert f3_item["status"] in ("awaiting_authorized_media", "awaiting_media")
    assert f3_item["commercial_use_allowed"] is True
    print(" -> PASS: Correctly halted at awaiting_authorized_media.")

    # Failure Test 4: Expired license remains blocked
    exp_vid = f"exp_{uid}___"[:11]
    s_resp = client.post(
        "/api/v1/discovery/sources",
        json={
            "video_id": exp_vid,
            "title": f"Expired Clip {uid}",
            "source_url": f"https://www.youtube.com/watch?v={exp_vid}",
            "duration_seconds": 60,
        },
    )
    exp_sid = s_resp.json()["id"]
    past_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    client.put(
        f"/api/v1/discovery/sources/{exp_sid}/rights",
        json={
            "permission_status": "authorized",
            "commercial_use_allowed": True,
            "license_documentation": "Contract expired 60 days ago",
            "expires_at": past_date,
        },
    )
    print(f"\n[Failure 4] Submitting source with license expired on {past_date}...")
    f4_resp = client.post("/api/v1/discovery/sources/batch?auto_process=true", json={"urls": [f"https://www.youtube.com/watch?v={exp_vid}"]})
    f4_item = client.get(f"/api/v1/discovery/batches/{f4_resp.json()['batch_id']}").json()["items"][0]
    print(f" -> Status: {f4_item['status']}")
    print(f" -> Diagnostic: {f4_item['error_message']}")
    assert f4_item["status"] in ("rights_rejected", "rejected")
    assert "expired" in (f4_item["error_message"] or "").lower()
    print(" -> PASS: Expired license blocked at rights gate.")

    # Failure Test 5: Corrupt master file fails safely
    corrupt_vid = f"cor_{uid}___"[:11]
    corrupt_file = Path(f"data/media/corrupt_{uid}.mp4").resolve()
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_VALID_MP4_HEADER_CORRUPTED_BYTES" * 10)  # corrupt file

    mapping_path = Path("storage/asset_mappings.json").resolve()
    mappings = {}
    if mapping_path.exists():
        try:
            with open(mapping_path, "r") as f:
                mappings = json.load(f)
        except Exception:
            mappings = {}
    mappings[corrupt_vid] = str(corrupt_file)
    with open(mapping_path, "w") as f:
        json.dump(mappings, f, indent=2)

    try:
        print(f"\n[Failure 5] Submitting video {corrupt_vid} pointing to corrupted file...")
        f5_resp = client.post(
            "/api/v1/discovery/sources/batch?auto_process=true",
            json={"creator_id": creator_id, "urls": [f"https://www.youtube.com/watch?v={corrupt_vid}"]},
        )
        f5_item = client.get(f"/api/v1/discovery/batches/{f5_resp.json()['batch_id']}").json()["items"][0]
        print(f" -> Status: {f5_item['status']}")
        print(f" -> Diagnostic: {f5_item['error_message']}")
        assert f5_item["status"] == "failed"
        assert "integrity" in (f5_item["error_message"] or "").lower() or "corrupt" in (f5_item["error_message"] or "").lower()
        print(" -> PASS: Corrupt master file detected and failed safely.")
    finally:
        if corrupt_file.exists():
            corrupt_file.unlink()
        if corrupt_vid in mappings:
            del mappings[corrupt_vid]
            with open(mapping_path, "w") as f:
                json.dump(mappings, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL M10.2 ACCEPTANCE TESTS AND FAILURE SCENARIOS COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
