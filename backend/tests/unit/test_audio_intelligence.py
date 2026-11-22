"""Unit tests for VANTYX Genuine Audio Intelligence Engine.

Validates physical acoustic measurements from native FFmpeg filters:
- Complete silence fixture
- Constant-volume audio fixture
- Sudden audio peaks fixture
- Alternating loud/quiet sections fixture
- Video without audio stream fixture
- Missing media and execution failure handling
- Candidate selection scoring integration
"""

import os
import subprocess
import pytest
from app.core.config import settings
from app.db.models.intelligence import VideoScene
from app.modules.intelligence.audio_analyzer import AudioAnalyzer, AudioMetrics, SceneAudioMetrics
from app.modules.selection.service import SelectionService


@pytest.fixture(scope="module")
def ffmpeg_bin():
    return settings.get_ffmpeg_executable()


def test_audio_fixture_complete_silence(tmp_path, ffmpeg_bin):
    """Verify that pure silence yields minimum energy, full silence percentage, and lowest audio score."""
    silence_file = str(tmp_path / "pure_silence.mp4")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo:d=3",
        "-c:a", "aac",
        silence_file,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    # 1. Full track measurement
    metrics = AudioAnalyzer.analyze_audio_track(silence_file)
    assert metrics.has_audio_stream is True
    assert metrics.audio_available is True
    assert metrics.is_silent is True
    assert metrics.rms_energy_db is not None and metrics.rms_energy_db <= -60.0
    assert metrics.peak_amplitude_db is not None and metrics.peak_amplitude_db <= -60.0
    assert metrics.silence_percentage >= 95.0
    assert metrics.audio_profile == "silent"

    # 2. Scene-specific measurement
    scene_metrics = AudioAnalyzer.analyze_scene_audio(silence_file, 0.0, 3.0)
    assert scene_metrics.has_audio is True
    assert scene_metrics.is_silent is True
    assert scene_metrics.audio_score == 25.0
    assert scene_metrics.audio_tag == "audio:silent"


def test_audio_fixture_constant_volume(tmp_path, ffmpeg_bin):
    """Verify that a steady tone or background music yields healthy energy, narrow LRA, and constant_music profile."""
    const_file = str(tmp_path / "constant_tone.mp4")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "sine=frequency=440:d=4",
        "-c:a", "aac",
        const_file,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    metrics = AudioAnalyzer.analyze_audio_track(const_file)
    assert metrics.has_audio_stream is True
    assert metrics.audio_available is True
    assert metrics.is_silent is False
    assert metrics.rms_energy_db is not None and metrics.rms_energy_db > -30.0
    assert metrics.loudness_range_lu is not None and metrics.loudness_range_lu <= 1.5
    assert metrics.silence_percentage < 5.0
    assert metrics.is_constant_music is True
    assert metrics.audio_profile == "constant_music"

    # Scene measurement
    scene_metrics = AudioAnalyzer.analyze_scene_audio(const_file, 0.5, 3.5)
    assert scene_metrics.has_audio is True
    assert scene_metrics.is_silent is False
    assert scene_metrics.is_constant_music is True
    assert scene_metrics.audio_score >= 60.0
    assert scene_metrics.audio_tag == "audio:constant_music"


def test_audio_fixture_sudden_audio_peaks(tmp_path, ffmpeg_bin):
    """Verify that transient peaks are detected with high peak amplitude and crest factor."""
    peak_file = str(tmp_path / "sudden_peak.mp4")
    # Low background tone (-40dB) with a sharp 0.5s loud burst (0.95 -> -0.4dB)
    expr = r"if(between(t\,1.0\,1.5)\,0.95*sin(2*PI*880*t)\,0.01*sin(2*PI*220*t))"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", f"aevalsrc='{expr}':s=44100:d=3",
        "-c:a", "aac",
        peak_file,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    metrics = AudioAnalyzer.analyze_audio_track(peak_file)
    assert metrics.has_audio_stream is True
    assert metrics.audio_available is True
    assert metrics.peak_amplitude_db is not None and metrics.peak_amplitude_db >= -3.0
    assert metrics.rms_energy_db is not None
    # Peak is substantially higher than the average RMS level
    assert (metrics.peak_amplitude_db - metrics.rms_energy_db) >= 6.0

    # Measure scene segment covering the peak [1.0, 2.0]
    peak_scene = AudioAnalyzer.analyze_scene_audio(peak_file, 1.0, 2.0)
    assert peak_scene.peak_db is not None and peak_scene.peak_db >= -3.0
    assert peak_scene.audio_tag in ["audio:punchy_peak", "audio:dynamic"]


def test_audio_fixture_alternating_loud_quiet(tmp_path, ffmpeg_bin):
    """Verify that alternating sections yield significant dynamic variation (LRA) and silence intervals."""
    alt_file = str(tmp_path / "alternating_sections.mp4")
    # Alternates between quiet (-46dB) and loud (-2dB) every second
    expr = r"if(mod(floor(t)\,2)\,0.8*sin(2*PI*440*t)\,0.005*sin(2*PI*440*t))"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", f"aevalsrc='{expr}':s=44100:d=4",
        "-c:a", "aac",
        alt_file,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    metrics = AudioAnalyzer.analyze_audio_track(alt_file, silence_threshold_db=-30.0)
    assert metrics.has_audio_stream is True
    assert metrics.audio_available is True
    assert metrics.is_silent is False
    assert metrics.is_constant_music is False
    # Quiet intervals registered
    assert len(metrics.silence_intervals) >= 1
    assert metrics.silence_percentage > 10.0


def test_audio_fixture_video_without_audio(tmp_path, ffmpeg_bin):
    """Verify that video lacking an audio stream is safely handled and flagged as no_audio."""
    no_audio_file = str(tmp_path / "no_audio.mp4")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "color=c=blue:s=320x240:d=2",
        "-c:v", "libx264",
        "-an",
        no_audio_file,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    has_stream, err = AudioAnalyzer.probe_audio_stream(no_audio_file)
    assert has_stream is False
    assert err is None

    metrics = AudioAnalyzer.analyze_audio_track(no_audio_file)
    assert metrics.has_audio_stream is False
    assert metrics.audio_available is False
    assert metrics.audio_profile == "no_audio"

    scene_metrics = AudioAnalyzer.analyze_scene_audio(no_audio_file, 0.0, 2.0)
    assert scene_metrics.has_audio is False
    assert scene_metrics.audio_score == 25.0
    assert scene_metrics.audio_tag == "audio:no_audio"


def test_audio_missing_media_and_failure_handling(tmp_path):
    """Verify resilient error handling on non-existent or corrupted media."""
    # 1. Non-existent file
    missing = str(tmp_path / "non_existent_file.mp4")
    metrics = AudioAnalyzer.analyze_audio_track(missing)
    assert metrics.has_audio_stream is False
    assert metrics.audio_available is False
    assert "not found" in (metrics.error or "").lower()

    # 2. Corrupt file with invalid header
    corrupt = tmp_path / "corrupt_data.mp4"
    corrupt.write_bytes(b"INVALID_MEDIA_HEADER_CORRUPTED" * 50)
    corrupt_metrics = AudioAnalyzer.analyze_audio_track(str(corrupt))
    assert corrupt_metrics.has_audio_stream is False
    assert corrupt_metrics.audio_available is False

    # 3. Very short scene segment (< 0.3s)
    short_scene = AudioAnalyzer.analyze_scene_audio(missing, 1.0, 1.1)
    assert short_scene.audio_score == 25.0  # missing media floor


def test_audio_measurements_influence_candidate_selection():
    """Verify that genuine physical audio measurements directly modulate CandidateClip ranking."""
    # Scene 1: Dead silence
    scene_silent = VideoScene(
        id=101,
        job_id=1,
        source_id=1,
        start_time=0.0,
        end_time=30.0,
        scene_label="Silent Street Corner",
        description="Player standing idle with muted audio",
        action_intensity=0.5,
        excitement_score=0.5,
        tags=["idle"],
        audio_metrics={
            "has_audio": True,
            "is_silent": True,
            "rms_db": -70.0,
            "peak_db": -65.0,
            "loudness_range_lu": 0.0,
            "silence_ratio": 1.0,
        },
    )

    # Scene 2: High-energy punchy audio
    scene_punchy = VideoScene(
        id=102,
        job_id=1,
        source_id=1,
        start_time=30.0,
        end_time=60.0,
        scene_label="Bank Vault Explosion",
        description="Loud dynamic detonation with engine getaway",
        action_intensity=0.5,
        excitement_score=0.5,
        tags=["heist", "explosion"],
        audio_metrics={
            "has_audio": True,
            "is_silent": False,
            "rms_db": -16.0,
            "peak_db": -1.5,
            "loudness_range_lu": 8.5,
            "silence_ratio": 0.05,
        },
    )

    score_silent = SelectionService.evaluate_audio_quality(scene_silent)
    score_punchy = SelectionService.evaluate_audio_quality(scene_punchy)

    assert score_silent == 25.0
    assert score_punchy >= 85.0
    assert score_punchy > score_silent + 50.0

    # Calculate overall candidate scores
    _, _, _, _, overall_silent, rat_silent, _ = SelectionService.calculate_scores(scene_silent)
    _, _, _, _, overall_punchy, rat_punchy, _ = SelectionService.calculate_scores(scene_punchy)

    assert overall_punchy > overall_silent
    assert "Muted/silent audio" in rat_silent
    assert "Dynamic audio punch" in rat_punchy
