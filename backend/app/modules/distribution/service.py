"""Distribution Service Interface.

Defines the contract for scheduling, channel authorization, and publishing.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DistributionServiceInterface(ABC):
    """Abstract interface defining the content distribution domain boundary."""

    @abstractmethod
    async def get_channel_status(self) -> Dict[str, Any]:
        """Retrieve authorized publishing channel status."""
        pass

    @abstractmethod
    async def list_scheduled_releases(self) -> List[Dict[str, Any]]:
        """List scheduled video publications."""
        pass


class DistributionService(DistributionServiceInterface):
    """Distribution service foundation implementation."""

    def __init__(self) -> None:
        self.is_active = False

    async def get_channel_status(self) -> Dict[str, Any]:
        """Channel connection status placeholder."""
        return {
            "authorized": False,
            "channel_id": None,
            "status": "unconfigured",
        }

    async def list_scheduled_releases(self) -> List[Dict[str, Any]]:
        """Scheduled releases placeholder."""
        return []
