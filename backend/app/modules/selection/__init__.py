"""VANTYX Selection Module.

Responsibility:
- Moment identification and viral retention scoring.
- Hook candidate detection and timestamp boundary selection.
- Ranking candidate segments based on historical channel signals.
"""

from .service import SelectionService

__all__ = ["SelectionService"]
