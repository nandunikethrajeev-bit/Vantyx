"""VANTYX Audio Intelligence Analyzer.

Performs genuine, measurable acoustic and audio-signal analysis using native FFmpeg filters:
- RMS audio energy (astats)
- Peak amplitude (astats)
- Integrated loudness and Loudness Range (ebur128)
- Silence interval detection (silencedetect)
- Scene-specific audio activity and quality scoring for clip candidate selection.
"""

import os
import re
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger


@dataclass
class AudioMetrics:
    has_audio_stream: bool
    audio_available: bool
    rms_energy_db: Optional[float] = None
    peak_amplitude_db: Optional[float] = None
    loudness_lufs: Optional[float] = None
    loudness_range_lu: Optional[float] = None
    silence_intervals: Optional[List[Dict[str, float]]] = None
    total_silence_duration: float = 0.0
    silence_percentage: float = 0.0
    is_constant_music: bool = False
    is_silent: bool = False
    audio_profile: str = "no_audio"  # silent | constant_music | dynamic_gameplay | quiet | normal | no_audio
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SceneAudioMetrics:
    start_time: float
    end_time: float
    duration_seconds: float
    has_audio: bool
    rms_db: Optional[float] = None
    peak_db: Optional[float] = None
    loudness_lufs: Optional[float] = None
    loudness_range_lu: Optional[float] = None
    silence_seconds: float = 0.0
    silence_ratio: float = 0.0
    is_silent: bool = False
    is_constant_music: bool = False
    audio_score: float = 55.0
    audio_tag: str = "audio:normal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AudioAnalyzer:
    """Native FFmpeg-based audio intelligence analyzer."""

    @staticmethod
    def probe_audio_stream(video_path: str, timeout: float = 10.0) -> Tuple[bool, Optional[str]]:
        """Determine whether a media file exists and contains an audio stream.
        
        Returns:
            Tuple of (has_audio_stream, error_message)
        """
        if not video_path or not os.path.exists(video_path):
            return False, f"Media file not found: {video_path}"

        ffmpeg_exe = settings.get_ffmpeg_executable()
        try:
            res = subprocess.run(
                [ffmpeg_exe, "-i", video_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            for line in res.stderr.splitlines():
                if "Stream #" in line and "Audio:" in line:
                    return True, None
            return False, None
        except Exception as exc:
            logger.warning(f"Audio stream probe failed on {video_path}: {exc}")
            return False, str(exc)

    @classmethod
    def analyze_audio_track(
        cls,
        video_path: str,
        silence_threshold_db: float = -30.0,
        silence_min_duration: float = 0.5,
        timeout: float = 60.0,
    ) -> AudioMetrics:
        """Execute full acoustic measurement pass on source video using astats, ebur128, and silencedetect."""
        if not video_path or not os.path.exists(video_path):
            return AudioMetrics(
                has_audio_stream=False,
                audio_available=False,
                error=f"Media file not found: {video_path}",
            )

        has_audio, err = cls.probe_audio_stream(video_path, timeout=10.0)
        if not has_audio:
            return AudioMetrics(
                has_audio_stream=False,
                audio_available=False,
                audio_profile="no_audio",
                error=err,
            )

        ffmpeg_exe = settings.get_ffmpeg_executable()
        filter_str = (
            f"astats,ebur128,silencedetect=noise={silence_threshold_db}dB:d={silence_min_duration}"
        )
        cmd = [
            ffmpeg_exe,
            "-i",
            video_path,
            "-vn",
            "-af",
            filter_str,
            "-f",
            "null",
            "-",
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return cls._parse_audio_metrics(res.stderr)
        except subprocess.TimeoutExpired:
            logger.warning(f"Audio analysis timed out after {timeout}s on {video_path}")
            return AudioMetrics(
                has_audio_stream=True,
                audio_available=False,
                error=f"FFmpeg analysis timed out after {timeout}s",
            )
        except Exception as exc:
            logger.error(f"FFmpeg audio analysis failed on {video_path}: {exc}")
            return AudioMetrics(
                has_audio_stream=True,
                audio_available=False,
                error=str(exc),
            )

    @classmethod
    def analyze_scene_audio(
        cls,
        video_path: str,
        start_time: float,
        end_time: float,
        has_audio_stream: Optional[bool] = None,
        timeout: float = 30.0,
    ) -> SceneAudioMetrics:
        """Measure acoustic properties for a specific scene segment [start_time, end_time]."""
        duration = max(0.1, round(end_time - start_time, 2))

        if not video_path or not os.path.exists(video_path):
            return SceneAudioMetrics(
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                has_audio=False,
                audio_score=25.0,
                audio_tag="audio:no_audio",
            )

        if has_audio_stream is None:
            has_audio_stream, _ = cls.probe_audio_stream(video_path, timeout=5.0)

        if not has_audio_stream:
            return SceneAudioMetrics(
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                has_audio=False,
                audio_score=25.0,
                audio_tag="audio:no_audio",
            )

        # Extremely short segments cannot produce robust statistics
        if duration < 0.3:
            return SceneAudioMetrics(
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                has_audio=True,
                audio_score=50.0,
                audio_tag="audio:short_segment",
            )

        ffmpeg_exe = settings.get_ffmpeg_executable()
        filter_str = "astats,ebur128,silencedetect=noise=-30dB:d=0.3"
        cmd = [
            ffmpeg_exe,
            "-ss",
            f"{start_time:.3f}",
            "-to",
            f"{end_time:.3f}",
            "-i",
            video_path,
            "-vn",
            "-af",
            filter_str,
            "-f",
            "null",
            "-",
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            metrics = cls._parse_audio_metrics(res.stderr, clip_duration=duration)

            rms = metrics.rms_energy_db
            peak = metrics.peak_amplitude_db
            lra = metrics.loudness_range_lu
            silence_ratio = metrics.silence_percentage / 100.0 if metrics.silence_percentage else 0.0

            audio_score = cls.calculate_scene_audio_score(
                has_audio=metrics.has_audio_stream and metrics.audio_available,
                rms_db=rms,
                peak_db=peak,
                loudness_range_lu=lra,
                silence_ratio=silence_ratio,
                is_constant_music=metrics.is_constant_music,
                is_silent=metrics.is_silent,
            )

            # Determine appropriate descriptive tag
            if metrics.is_silent:
                tag = "audio:silent"
            elif metrics.is_constant_music:
                tag = "audio:constant_music"
            elif lra is not None and lra >= 5.0:
                tag = "audio:dynamic"
            elif peak is not None and peak >= -2.0:
                tag = "audio:punchy_peak"
            elif rms is not None and rms < -35.0:
                tag = "audio:quiet"
            else:
                tag = "audio:normal"

            return SceneAudioMetrics(
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                has_audio=metrics.audio_available,
                rms_db=rms,
                peak_db=peak,
                loudness_lufs=metrics.loudness_lufs,
                loudness_range_lu=lra,
                silence_seconds=metrics.total_silence_duration,
                silence_ratio=round(silence_ratio, 3),
                is_silent=metrics.is_silent,
                is_constant_music=metrics.is_constant_music,
                audio_score=audio_score,
                audio_tag=tag,
            )

        except Exception as exc:
            logger.warning(f"Scene audio analysis error [{start_time}-{end_time}]: {exc}")
            return SceneAudioMetrics(
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                has_audio=True,
                audio_score=50.0,
                audio_tag="audio:unmeasured",
            )

    @classmethod
    def _parse_audio_metrics(cls, stderr: str, clip_duration: Optional[float] = None) -> AudioMetrics:
        """Extract acoustic measurements from FFmpeg astats, ebur128, and silencedetect logs."""
        peak_val: Optional[float] = None
        rms_val: Optional[float] = None
        lufs_val: Optional[float] = None
        lra_val: Optional[float] = None

        # 1. Parse Peak and RMS from astats
        peak_matches = re.findall(r"Peak level dB:\s+(-?inf|[-\d\.]+)", stderr)
        if peak_matches:
            raw_peak = peak_matches[-1].strip()
            peak_val = -96.0 if "inf" in raw_peak else round(float(raw_peak), 2)

        rms_matches = re.findall(r"RMS level dB:\s+(-?inf|[-\d\.]+)", stderr)
        if rms_matches:
            raw_rms = rms_matches[-1].strip()
            rms_val = -96.0 if "inf" in raw_rms else round(float(raw_rms), 2)

        # 2. Parse Integrated Loudness (I) and Loudness Range (LRA) from ebur128 Summary
        summary_idx = stderr.rfind("Summary:")
        summary_text = stderr[summary_idx:] if summary_idx != -1 else stderr

        i_match = re.search(r"I:\s+([-\d\.]+)\s+LUFS", summary_text)
        if i_match:
            lufs_val = round(float(i_match.group(1)), 1)

        lra_match = re.search(r"LRA:\s+([-\d\.]+)\s+LU", summary_text)
        if lra_match:
            lra_val = round(float(lra_match.group(1)), 1)

        # 3. Parse Silence intervals
        silence_intervals: List[Dict[str, float]] = []
        total_silence = 0.0

        silence_starts = [float(m) for m in re.findall(r"silence_start:\s+([-\d\.]+)", stderr)]
        silence_ends_durs = re.findall(r"silence_end:\s+([-\d\.]+)\s+\|\s+silence_duration:\s+([-\d\.]+)", stderr)

        for end_str, dur_str in silence_ends_durs:
            end_t = float(end_str)
            dur = float(dur_str)
            start_t = max(0.0, end_t - dur)
            silence_intervals.append({"start": round(start_t, 2), "end": round(end_t, 2), "duration": round(dur, 2)})
            total_silence += dur

        # Handle unclosed silence interval at the end of the media
        if len(silence_starts) > len(silence_ends_durs) and clip_duration:
            last_start = silence_starts[-1]
            dur = max(0.0, clip_duration - last_start)
            silence_intervals.append({"start": round(last_start, 2), "end": round(clip_duration, 2), "duration": round(dur, 2)})
            total_silence += dur

        # 4. Total duration estimation
        total_duration = clip_duration
        if total_duration is None:
            time_matches = re.findall(r"time=(\d+):(\d+):([\d\.]+)", stderr)
            if time_matches:
                last_t = time_matches[-1]
                total_duration = int(last_t[0]) * 3600 + int(last_t[1]) * 60 + float(last_t[2])

        total_duration = total_duration or 1.0
        silence_pct = round(min(100.0, (total_silence / total_duration) * 100.0), 1)

        # 5. Classify profiles
        is_silent = (rms_val is not None and rms_val <= -60.0) or (peak_val is not None and peak_val <= -60.0) or silence_pct >= 98.0

        is_constant_music = False
        if not is_silent and rms_val is not None and rms_val > -28.0:
            if lra_val is not None and lra_val <= 1.5 and silence_pct < 5.0:
                is_constant_music = True

        if is_silent:
            profile = "silent"
        elif is_constant_music:
            profile = "constant_music"
        elif (lra_val is not None and lra_val >= 5.0) or silence_pct > 15.0:
            profile = "dynamic_gameplay"
        elif rms_val is not None and rms_val < -35.0:
            profile = "quiet"
        else:
            profile = "normal"

        return AudioMetrics(
            has_audio_stream=True,
            audio_available=True,
            rms_energy_db=rms_val,
            peak_amplitude_db=peak_val,
            loudness_lufs=lufs_val,
            loudness_range_lu=lra_val,
            silence_intervals=silence_intervals,
            total_silence_duration=round(total_silence, 2),
            silence_percentage=silence_pct,
            is_constant_music=is_constant_music,
            is_silent=is_silent,
            audio_profile=profile,
        )

    @staticmethod
    def calculate_scene_audio_score(
        has_audio: bool,
        rms_db: Optional[float] = None,
        peak_db: Optional[float] = None,
        loudness_range_lu: Optional[float] = None,
        silence_ratio: float = 0.0,
        is_constant_music: bool = False,
        is_silent: bool = False,
        has_speech: bool = False,
    ) -> float:
        """Calculate a bounded 25.0 - 100.0 audio quality and engagement score from physical acoustic measurements."""
        if not has_audio or is_silent or (rms_db is not None and rms_db <= -55.0):
            return 25.0  # Floor score for absent, dead, or muted audio

        # Base presence score for verified audible track
        score = 50.0

        # 1. RMS Energy / Audibility Component (Target: -24 dB to -12 dB for online Shorts)
        if rms_db is not None:
            if -24.0 <= rms_db <= -12.0:
                score += 15.0  # Optimal clarity
            elif -35.0 <= rms_db < -24.0:
                score += 8.0   # Acceptable dialogue/gameplay
            elif rms_db > -12.0:
                score += 10.0  # Compressed or loud action
            else:
                score -= 10.0  # Very faint audio

        # 2. Peak Amplitude Headroom Component (Target: -6.0 dB to -0.5 dB)
        if peak_db is not None:
            if -6.0 <= peak_db <= -0.5:
                score += 15.0  # Punchy, energetic dynamic transients
            elif -15.0 <= peak_db < -6.0:
                score += 8.0   # Moderate transients
            elif peak_db > -0.5:
                score += 5.0   # Clipping or saturated peaks
            else:
                score -= 5.0   # Weak peaks

        # 3. Dynamic Range / Variation Component (LRA)
        if loudness_range_lu is not None:
            if loudness_range_lu >= 5.0:
                score += 15.0  # Rich dynamic variation (action/quiet contrast)
            elif loudness_range_lu >= 2.0:
                score += 8.0   # Moderate variation
            elif is_constant_music or loudness_range_lu < 1.5:
                score += 4.0   # Constant volume background music/drone

        # 4. Silence Penalty (penalize prolonged dead silence in short-form content)
        if silence_ratio > 0.40:
            score -= 18.0
        elif silence_ratio > 0.20:
            score -= 8.0

        # 5. Speech bonus if commentary or dialogue is present
        if has_speech:
            score += 10.0

        return round(min(100.0, max(25.0, score)), 1)
