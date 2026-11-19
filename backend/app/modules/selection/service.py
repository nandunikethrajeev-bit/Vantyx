"""Selection Service Interface.

Defines the contract for scoring moments and selecting candidate clip boundaries.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class SelectionServiceInterface(ABC):
    """Abstract interface defining the clip selection domain boundary."""

    @abstractmethod
    async def rank_candidate_moments(self, video_id: str) -> List[Dict[str, Any]]:
        """Rank candidate moments based on engagement potential."""
        pass


class SelectionService(SelectionServiceInterface):
    """Selection service foundation implementation."""

    def __init__(self) -> None:
        self.is_active = False

    async def rank_candidate_moments(self, video_id: str) -> List[Dict[str, Any]]:
        """Foundation moment ranking placeholder."""
        return []
