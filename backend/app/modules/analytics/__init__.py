"""VANTYX Analytics Module.

Responsibility:
- Post-publish performance tracking (views, average percentage viewed, engagement).
- Feedback loop ingestion to refine future moment selection weights.
- Metric aggregation and reporting.
"""

from .service import AnalyticsService

__all__ = ["AnalyticsService"]
