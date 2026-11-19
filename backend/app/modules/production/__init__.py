"""VANTYX Production Module.

Responsibility:
- Vertical video synthesis (9:16 re-framing, dynamic crop).
- Subtitle generation, typographic rendering, and audio ducking/mastering.
- Media encoding and render task isolation.
"""

from .service import ProductionService

__all__ = ["ProductionService"]
