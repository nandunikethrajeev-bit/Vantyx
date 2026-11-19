"""Intelligence Service Interface.

Defines the contract for multimodal video intelligence and scene understanding.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IntelligenceServiceInterface(ABC):
    """Abstract interface defining the intelligence domain boundary."""

    @abstractmethod
    async def analyze_video(self, video_id: str) -> Dict[str, Any]:
        """Analyze a video and produce structural semantic markers."""
        pass


class IntelligenceService(IntelligenceServiceInterface):
    """Intelligence service foundation implementation."""

    def __init__(self) -> None:
        self.is_active = False

    async def analyze_video(self, video_id: str) -> Dict[str, Any]:
        """Foundation analysis placeholder."""
        return {
            "video_id": video_id,
            "status": "unprocessed",
            "scenes": [],
        }
