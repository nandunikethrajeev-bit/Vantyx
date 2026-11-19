"""Production Service Interface.

Defines the contract for video rendering, vertical composition, and subtitle generation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ProductionServiceInterface(ABC):
    """Abstract interface defining the video production domain boundary."""

    @abstractmethod
    async def render_short(self, segment_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger render task for a vertical short video."""
        pass


class ProductionService(ProductionServiceInterface):
    """Production service foundation implementation."""

    def __init__(self) -> None:
        self.is_active = False

    async def render_short(self, segment_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Foundation video production placeholder."""
        return {
            "segment_id": segment_id,
            "status": "idle",
            "output_path": None,
        }
