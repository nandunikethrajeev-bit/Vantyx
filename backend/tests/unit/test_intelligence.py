"""Unit tests for AI Intelligence Engine and Provider abstractions."""

import pytest
from app.db.models.source import VideoSource
from app.modules.intelligence.service import (
    GeminiAIProvider,
    HeuristicAIProvider,
    IntelligenceService,
)


@pytest.mark.asyncio
async def test_heuristic_provider_scene_generation():
    """Verify HeuristicAIProvider parses metadata and creates non-overlapping scenes without fabricated speech."""
    provider = HeuristicAIProvider()
    source = VideoSource(
        video_id="gta_test_01",
        title="GTA 6 Epic Bank Heist Escape Police Chase",
        description="High speed tactical getaway through Vice City downtown with 5 stars.",
        duration_seconds=360,
        source_url="https://youtube.com/watch?v=gta_test_01",
    )

    scenes = await provider.analyze_video(source)
    assert len(scenes) >= 3

    for s in scenes:
        assert s["start_time"] < s["end_time"]
        assert s["end_time"] <= source.duration_seconds
        assert 0.0 <= s["action_intensity"] <= 1.0
        assert 0.0 <= s["excitement_score"] <= 1.0
        assert len(s["tags"]) > 0
        # Truthful separation: speech transcription is not fabricated
        assert s.get("speech_transcript") is None


def test_provider_selection():
    """Verify provider factory returns appropriate instance."""
    p_heuristic = IntelligenceService.get_provider("heuristic")
    assert isinstance(p_heuristic, HeuristicAIProvider)

    p_gemini = IntelligenceService.get_provider("gemini")
    assert isinstance(p_gemini, GeminiAIProvider)


@pytest.mark.asyncio
async def test_provider_identity_and_fallback_transparency():
    """Verify provider identity is strictly distinguished and unconfigured Gemini falls back cleanly."""
    p_heuristic = HeuristicAIProvider()
    assert p_heuristic.__class__.__name__ == "HeuristicAIProvider"

    # Gemini with empty API key must fall back to Heuristic
    p_gemini_empty = GeminiAIProvider(api_key="")
    assert p_gemini_empty.__class__.__name__ == "GeminiAIProvider"

    source = VideoSource(
        video_id="synth_test_id",
        title="SYNTHETIC_TEST_ONLY Vice City Heist",
        duration_seconds=60,
        source_url="file:///synthetic.mp4",
    )
    scenes = await p_gemini_empty.analyze_video(source)
    assert p_gemini_empty.last_used_provider in ("heuristic", "heuristic_fallback")
    assert len(scenes) >= 1
    assert scenes[0].get("provider_used") == "heuristic"


def test_heuristic_single_scene_and_duration_partitioning():
    """Verify single continuous footage handling and duration partitioning without cuts."""
    source_short = VideoSource(
        video_id="continuous_test_60s",
        title="Vice City Bank Heist Pursuit",
        duration_seconds=60,
        source_url="file:///continuous.mp4",
    )
    import asyncio
    scenes_short = asyncio.run(HeuristicAIProvider().analyze_video(source_short))
    # A 60s video without visual cuts is treated as continuous uncut footage
    assert len(scenes_short) == 1
    assert scenes_short[0]["start_time"] == 0.0
    assert scenes_short[0]["end_time"] == 60.0
    assert "Continuous" in scenes_short[0]["scene_label"]
    assert scenes_short[0]["speech_transcript"] is None

    # Long-form video (360s) partitions into 45s candidate segments
    source_long = VideoSource(
        video_id="partition_test_360s",
        title="Vice City Bank Heist Pursuit",
        duration_seconds=360,
        source_url="file:///long.mp4",
    )
    scenes_long = asyncio.run(HeuristicAIProvider().analyze_video(source_long))
    assert len(scenes_long) >= 4
    for sc in scenes_long:
        assert sc["speech_transcript"] is None


def test_ffmpeg_boundaries_flow_into_heuristic_provider():
    """Verify FFmpeg visual cut timestamps flow into scene generation and produce exact scenes."""
    source = VideoSource(
        video_id="cut_test_60s",
        title="Vice City Multi-Scene Heist Lab",
        duration_seconds=60,
        source_url="file:///cuts.mp4",
    )
    import asyncio
    # 4 distinct 15s scenes defined by cuts at 15.0, 30.0, 45.0
    cuts = [15.0, 30.0, 45.0]
    scenes = asyncio.run(HeuristicAIProvider().analyze_video(source, scene_cuts=cuts))

    assert len(scenes) == 4
    expected_ranges = [(0.0, 15.0), (15.0, 30.0), (30.0, 45.0), (45.0, 60.0)]
    for idx, (exp_start, exp_end) in enumerate(expected_ranges, 1):
        sc = scenes[idx - 1]
        assert sc["start_time"] == exp_start
        assert sc["end_time"] == exp_end
        assert f"Visual Scene #{idx}" in sc["scene_label"]
        assert "visual_cut" in sc["tags"]
        assert sc["speech_transcript"] is None


def test_missing_and_invalid_video_files_handling():
    """Verify missing, empty, or unreadable video files gracefully return empty cut list."""
    assert IntelligenceService.detect_scene_cuts_ffmpeg(None) == []
    assert IntelligenceService.detect_scene_cuts_ffmpeg("") == []
    assert IntelligenceService.detect_scene_cuts_ffmpeg("non_existent_path_xyz123.mp4") == []


def test_no_cut_and_micro_cut_scene_building():
    """Verify build_scenes_from_cuts merges micro-cuts and handles zero cuts gracefully."""
    # Zero cuts
    assert HeuristicAIProvider.build_scenes_from_cuts([], total_duration=45.0) == [(0.0, 45.0)]

    # Micro-cuts under 12s merged
    cuts = [2.0, 5.0, 20.0]
    scenes = HeuristicAIProvider.build_scenes_from_cuts(cuts, total_duration=30.0, min_scene_duration=12.0)
    # 0->2 and 2->5 are under 12s, merged with 5->20 to make 0->20 (20s)
    # 20->30 is 10s < 12s, merged to make 0->30 (30s)
    assert scenes == [(0.0, 30.0)]


def test_native_ffmpeg_scene_cut_detection():
    """Verify native FFmpeg scene detection accurately detects visual cuts on real test footage."""
    import os
    from pathlib import Path
    test_media = Path("data/media/synthetic_test_footage_1080p.mp4")
    if not test_media.exists():
        pytest.skip("Synthetic test media not found on disk")

    cuts = IntelligenceService.detect_scene_cuts_ffmpeg(str(test_media), threshold=0.02)
    # The 60s synthetic video has 4 distinct 15s scenes with visual cuts at 15.0s, 30.0s, and 45.0s
    assert len(cuts) == 3
    assert abs(cuts[0] - 15.0) < 0.5
    assert abs(cuts[1] - 30.0) < 0.5
    assert abs(cuts[2] - 45.0) < 0.5
