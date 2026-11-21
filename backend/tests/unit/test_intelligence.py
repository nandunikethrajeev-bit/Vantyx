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
    """Verify HeuristicAIProvider parses metadata and creates non-overlapping scenes."""
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
        assert len(s["speech_transcript"]) > 0


def test_provider_selection():
    """Verify provider factory returns appropriate instance."""
    p_heuristic = IntelligenceService.get_provider("heuristic")
    assert isinstance(p_heuristic, HeuristicAIProvider)

    p_gemini = IntelligenceService.get_provider("gemini")
    assert isinstance(p_gemini, GeminiAIProvider)
