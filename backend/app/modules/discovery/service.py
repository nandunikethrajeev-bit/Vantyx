"""Discovery Service Interface.

Defines the contract for video discovery, creator validation, and source qualification.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DiscoveryServiceInterface(ABC):
    """Abstract interface defining the discovery domain boundary."""

    @abstractmethod
    async def list_approved_sources(self) -> List[Dict[str, Any]]:
        """Retrieve the catalog of approved creators and content sources."""
        pass

    @abstractmethod
    async def validate_source_rights(self, source_id: str) -> bool:
        """Validate commercial and attribution rights for a given source."""
        pass


class DiscoveryService(DiscoveryServiceInterface):
    """Discovery service foundation implementation."""

    def __init__(self) -> None:
        self.is_active = False

    async def list_approved_sources(self) -> List[Dict[str, Any]]:
        """Return currently configured discovery sources."""
        return []

    async def validate_source_rights(self, source_id: str) -> bool:
        """Verify copyright and permission compliance."""
        return False
