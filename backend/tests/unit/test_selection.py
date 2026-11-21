"""Unit tests for Clip Selection scoring, deduplication, weights, and overlap resolution."""

import pytest
from app.db.models.intelligence import VideoScene
from app.modules.selection.service import RankingWeights, SelectionService


@pytest.fixture
def high_energy_scene() -> VideoScene:
    """Deterministic fixture for high-energy optimal action scene."""
    return VideoScene(
        id=1,
        job_id=1,
        source_id=1,
        start_time=10.0,
        end_time=52.0,  # 42 seconds (ideal shorts sweetspot)
        scene_label="GTA 6 Vice City Helicopter Stunt Chase",
        description="Jason evades police cruisers with an aerial helicopter maneuver.",
        speech_transcript="Hold on tight, we are jumping across the canal!",
        action_intensity=0.88,
        excitement_score=0.92,
        tags=["action", "stunt", "chase", "dialogue", "engine"],
    )


@pytest.fixture
def low_energy_fragmented_scene() -> VideoScene:
    """Deterministic fixture for a short, low-energy fragmented scene."""
    return VideoScene(
        id=2,
        job_id=1,
        source_id=1,
        start_time=100.0,
        end_time=114.0,  # 14 seconds (too short for narrative arc)
        scene_label="Quiet convenience store interior",
        description="Looking at drinks inside the shop.",
        speech_transcript=None,
        action_intensity=0.20,
        excitement_score=0.25,
        tags=["ambient", "interior"],
    )


def test_score_calculation(high_energy_scene: VideoScene):
    """Verify hook, retention, context, audio, and overall score calculations."""
    hook, ret, ctx, aud, overall, rationale, title = SelectionService.calculate_scores(high_energy_scene)
    assert 20.0 <= hook <= 100.0
    assert 15.0 <= ret <= 100.0
    assert 20.0 <= ctx <= 100.0
    assert 25.0 <= aud <= 100.0
    assert 0.0 <= overall <= 100.0

    # High energy scene checks
    assert hook >= 75.0, "High energy scene with tags & speech should yield high hook score"
    assert ret >= 75.0, "High excitement and action should yield high retention score"
    assert ctx >= 85.0, "42s duration should yield near-optimal context completeness"
    assert aud >= 75.0, "Scene with speech transcript & dialogue tag should have high audio score"
    assert "Optimal Shorts duration" in rationale
    assert "#Shorts" in title


def test_hook_strength_evaluation(high_energy_scene: VideoScene, low_energy_fragmented_scene: VideoScene):
    """Verify hook strength evaluator rewards action intensity, speech, and high-hook tags."""
    high_hook = SelectionService.evaluate_hook_strength(high_energy_scene)
    low_hook = SelectionService.evaluate_hook_strength(low_energy_fragmented_scene)
    assert high_hook > low_hook
    assert high_hook >= 80.0
    assert low_hook < 50.0


def test_context_completeness(high_energy_scene: VideoScene, low_energy_fragmented_scene: VideoScene):
    """Verify context completeness penalizes overly short fragmented scenes (<20s)."""
    optimal_ctx = SelectionService.evaluate_context_completeness(high_energy_scene, 42.0)
    fragmented_ctx = SelectionService.evaluate_context_completeness(low_energy_fragmented_scene, 14.0)
    assert optimal_ctx > fragmented_ctx
    assert optimal_ctx >= 85.0
    assert fragmented_ctx < 60.0


def test_audio_quality_assessment(high_energy_scene: VideoScene, low_energy_fragmented_scene: VideoScene):
    """Verify audio assessment scores voice and sound design higher than silent/ambient."""
    rich_audio = SelectionService.evaluate_audio_quality(high_energy_scene)
    plain_audio = SelectionService.evaluate_audio_quality(low_energy_fragmented_scene)
    assert rich_audio > plain_audio
    assert rich_audio >= 80.0


def test_configurable_ranking_weights(high_energy_scene: VideoScene):
    """Verify customizable weights dynamically adjust the overall ranking score."""
    # Weight prioritizing hook vs weight prioritizing audio
    hook_focused = RankingWeights(hook_weight=0.8, retention_weight=0.1, context_weight=0.05, audio_weight=0.05)
    normalized = hook_focused.normalize()
    assert abs(normalized.hook_weight + normalized.retention_weight + normalized.context_weight + normalized.audio_weight - 1.0) < 0.01

    _, _, _, _, score_hook_favored, _, _ = SelectionService.calculate_scores(high_energy_scene, hook_focused)
    assert 70.0 <= score_hook_favored <= 100.0


def test_timestamp_overlap_prevention():
    """Verify strict timestamp interval overlap detection."""
    chosen = [
        {"start_time": 10.0, "end_time": 45.0},
        {"start_time": 100.0, "end_time": 140.0},
    ]
    # Overlapping interval (20 to 50 overlaps with 10 to 45 by 25s)
    assert SelectionService.has_timestamp_overlap(20.0, 50.0, chosen, tolerance_seconds=3.0) is True

    # Non-overlapping interval (50 to 90 is distinct)
    assert SelectionService.has_timestamp_overlap(50.0, 90.0, chosen, tolerance_seconds=3.0) is False

    # Minimal edge touch within tolerance (45 to 80 touches at 45.0, overlap <= 3.0)
    assert SelectionService.has_timestamp_overlap(45.0, 80.0, chosen, tolerance_seconds=3.0) is False


def test_duplicate_moment_detection():
    """Verify duplicate theme or identical scene moment detection."""
    chosen = [
        {
            "tokens": {"gta", "vice", "city", "helicopter", "chase", "action", "stunt"},
            "start_time": 10.0,
            "end_time": 45.0,
        }
    ]

    # Similar scene (high Jaccard similarity in tokens)
    candidate_tags = {"helicopter", "chase", "action", "stunt"}
    candidate_label = "GTA 6 Helicopter Stunt Chase"
    is_dup = SelectionService.is_duplicate_moment(candidate_tags, candidate_label, chosen, similarity_threshold=0.6)
    assert is_dup is True

    # Completely different scene
    different_tags = {"stealth", "mansion", "night"}
    different_label = "Sneaking into cartel safehouse"
    is_not_dup = SelectionService.is_duplicate_moment(different_tags, different_label, chosen, similarity_threshold=0.6)
    assert is_not_dup is False
