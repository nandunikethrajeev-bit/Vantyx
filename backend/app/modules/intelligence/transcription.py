"""VANTYX Speech Transcription Subsystem.

Provides pluggable transcription provider interface with strict transparency guarantees.
When no local ASR engine (e.g. Whisper) or authorized speech API is configured,
it explicitly reports transcription as unavailable rather than fabricating or hallucinating
fake quotes or commentary.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.logging import logger


class TranscriptionProviderInterface(ABC):
    """Abstract interface defining the speech recognition domain boundary."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if speech recognition engine is initialized and ready."""
        pass

    @abstractmethod
    async def transcribe_segment(
        self,
        media_path: str,
        start_time: float,
        end_time: float,
    ) -> Optional[str]:
        """Transcribe speech in the given time window, or return None if no speech / engine unavailable."""
        pass

    @abstractmethod
    def get_status_summary(self) -> Dict[str, Any]:
        """Return truthful capability and status dictionary."""
        pass


class UnavailableTranscriptionProvider(TranscriptionProviderInterface):
    """Default honest fallback: reports ASR as unavailable and never fabricates transcripts."""

    def is_available(self) -> bool:
        return False

    async def transcribe_segment(
        self,
        media_path: str,
        start_time: float,
        end_time: float,
    ) -> Optional[str]:
        # Truthful disclosure: no automated speech recognition model is active
        return None

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "status": "unavailable",
            "provider": "none",
            "message": "Automated speech recognition (ASR) not configured. Spoken transcripts disabled.",
            "is_operational": False,
        }


def get_transcription_provider() -> TranscriptionProviderInterface:
    """Retrieve active transcription provider based on configuration."""
    # In future, if local whisper or faster-whisper is installed and configured in settings, instantiate here.
    return UnavailableTranscriptionProvider()
