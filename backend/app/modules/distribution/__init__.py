"""VANTYX Distribution Module.

Responsibility:
- Publishing queue and schedule orchestration.
- YouTube channel authorization status tracking.
- Metadata compilation (title, description, tags, hashtags) and release dispatch.
"""

from .service import DistributionService

__all__ = ["DistributionService"]
