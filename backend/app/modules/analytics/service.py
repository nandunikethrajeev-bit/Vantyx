"""Analytics Service Interface.

Defines the contract for audience retention metrics, video performance, and feedback loops.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class AnalyticsServiceInterface(ABC):
    """Abstract interface defining the analytics domain boundary."""

    @abstractmethod
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Retrieve aggregated video performance indicators."""
        pass


class AnalyticsService(AnalyticsServiceInterface):
    """Analytics service foundation implementation."""

    def __init__(self) -> None:
        self.is_active = False

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Performance summary placeholder."""
        return {
            "status": "inactive",
            "metrics_available": False,
        }
