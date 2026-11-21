"""Unit tests for production video filtergraphs (aspect ratio handling) and storage retention."""

import os
import time
from pathlib import Path
import pytest
from app.core.config import settings
from app.modules.production.service import ProductionService


def test_universal_aspect_ratio_filtergraph_16_9():
    """Verify cinematic blur backdrop filtergraph for standard 16:9 widescreen."""
    fg = ProductionService.build_video_filtergraph(layout_style="blurred_backdrop", src_width=1920, src_height=1080)
    assert "force_original_aspect_ratio=increase" in fg
    assert "force_original_aspect_ratio=decrease" in fg
    assert "boxblur=20:5" in fg
    assert "overlay=(W-w)/2:(H-h)/2" in fg


def test_universal_aspect_ratio_filtergraph_21_9_ultrawide():
    """Verify filtergraph cleanly handles 21:9 ultrawide without distortion."""
    fg = ProductionService.build_video_filtergraph(layout_style="blurred_backdrop", src_width=2560, src_height=1080)
    assert "force_original_aspect_ratio=increase" in fg
    assert "force_original_aspect_ratio=decrease" in fg
    assert "overlay=" in fg


def test_universal_aspect_ratio_filtergraph_4_3_retro():
    """Verify filtergraph cleanly handles 4:3 input."""
    fg = ProductionService.build_video_filtergraph(layout_style="blurred_backdrop", src_width=1440, src_height=1080)
    assert "force_original_aspect_ratio=increase" in fg
    assert "boxblur" in fg


def test_native_vertical_9_16_direct_scaling():
    """Verify native vertical video skips blur backdrop and scales directly."""
    fg = ProductionService.build_video_filtergraph(layout_style="blurred_backdrop", src_width=1080, src_height=1920)
    assert fg == "[0:v]scale=1080:1920,setsar=1[v]"


@pytest.mark.asyncio
async def test_storage_cleanup_policy(tmp_path, monkeypatch):
    """Verify cleanup_expired_storage purges files older than max_age_days."""
    monkeypatch.setattr(settings, "EXPORT_DIR", str(tmp_path))

    # Create dummy recent file (1 day old)
    recent_file = tmp_path / "vantyx_short_recent.mp4"
    recent_file.write_bytes(b"dummy_recent_content_12345")

    # Create dummy expired file (35 days old)
    expired_file = tmp_path / "vantyx_short_expired.mp4"
    expired_file.write_bytes(b"dummy_expired_content_67890")
    old_time = time.time() - (35 * 86400)
    os.utime(expired_file, (old_time, old_time))

    res = await ProductionService.cleanup_expired_storage(max_age_days=30, dry_run=False)

    assert res["deleted_files"] == 1
    assert recent_file.exists() is True
    assert expired_file.exists() is False
