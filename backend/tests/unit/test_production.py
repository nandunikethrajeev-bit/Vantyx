"""Unit tests for Video Production engine and FFmpeg filtergraph construction."""

import os
from app.core.config import settings
from app.modules.production.service import ProductionService


def test_ffmpeg_executable_resolution():
    """Verify FFmpeg binary path resolves and exists on the filesystem."""
    ffmpeg_exe = settings.get_ffmpeg_executable()
    assert ffmpeg_exe is not None
    assert os.path.exists(ffmpeg_exe), f"FFmpeg executable not found at {ffmpeg_exe}"


def test_filtergraph_construction():
    """Verify video filtergraphs for vertical 9:16 synthesis."""
    blurred_fg = ProductionService.build_video_filtergraph("blurred_backdrop")
    assert "boxblur" in blurred_fg
    assert "scale=1080:1920" in blurred_fg
    assert "overlay" in blurred_fg

    crop_fg = ProductionService.build_video_filtergraph("crop_center")
    assert "crop=in_h*(9/16):in_h" in crop_fg
    assert "scale=1080:1920" in crop_fg
