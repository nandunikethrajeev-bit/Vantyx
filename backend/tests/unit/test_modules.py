"""Unit tests for modular monolith subsystem boundaries."""

import asyncio
from app.modules.discovery import DiscoveryService
from app.modules.intelligence import IntelligenceService
from app.modules.selection import SelectionService
from app.modules.production import ProductionService
from app.modules.distribution import DistributionService
from app.modules.analytics import AnalyticsService


def test_modular_service_interfaces():
    """Verify all domain modules instantiate and respond to defined interfaces."""
    async def _test():
        # Discovery
        discovery = DiscoveryService()
        assert discovery.is_active is False
        sources = await discovery.list_approved_sources()
        assert isinstance(sources, list)

        # Intelligence
        intelligence = IntelligenceService()
        assert intelligence.is_active is False
        analysis = await intelligence.analyze_video("test-vid-123")
        assert analysis["status"] == "unprocessed"

        # Selection
        selection = SelectionService()
        assert selection.is_active is False
        moments = await selection.rank_candidate_moments("test-vid-123")
        assert isinstance(moments, list)

        # Production
        production = ProductionService()
        assert production.is_active is False
        render = await production.render_short("test-seg-1", {})
        assert render["status"] == "idle"

        # Distribution
        distribution = DistributionService()
        assert distribution.is_active is False
        channel_status = await distribution.get_channel_status()
        assert channel_status["authorized"] is False

        # Analytics
        analytics = AnalyticsService()
        assert analytics.is_active is False
        summary = await analytics.get_performance_summary()
        assert summary["status"] == "inactive"

    asyncio.run(_test())
