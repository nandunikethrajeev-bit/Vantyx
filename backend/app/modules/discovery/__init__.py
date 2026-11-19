"""VANTYX Discovery Module.

Responsibility:
- Monitor and discover eligible GTA 6 gameplay videos from approved sources.
- Track source creator licenses, commercial-use rights, and origin attribution.
- Enforce ingestion policies and filter out non-qualifying candidate media.
"""

from .service import DiscoveryService

__all__ = ["DiscoveryService"]
