"""Unit tests for Discovery service and rights eligibility validation gate."""

from datetime import datetime, timedelta, timezone
from app.db.models.creator import Creator
from app.db.models.rights import RightsRecord
from app.db.models.source import VideoSource
from app.modules.discovery.service import DiscoveryService


def test_eligibility_without_rights():
    """A source without rights record must not be eligible."""
    source = VideoSource(video_id="v1", title="GTA 6 Chase", source_url="https://youtube.com/v1")
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is False
    assert "No rights" in reason


def test_eligibility_pending_permission():
    """A source with pending permission status must not enter production."""
    source = VideoSource(video_id="v2", title="GTA 6 Heist", source_url="https://youtube.com/v2")
    source.rights = RightsRecord(
        permission_status="pending",
        commercial_use_allowed=False,
    )
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is False
    assert "pending" in reason


def test_eligibility_authorized_without_commercial():
    """A source that is authorized for viewing but not commercial use must be blocked."""
    source = VideoSource(video_id="v3", title="GTA 6 Map", source_url="https://youtube.com/v3")
    source.rights = RightsRecord(
        permission_status="authorized",
        commercial_use_allowed=False,
    )
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is False
    assert "Commercial-use" in reason


def test_eligibility_expired_rights():
    """Expired licenses must fail the eligibility gate."""
    source = VideoSource(video_id="v4", title="GTA 6 Drift", source_url="https://youtube.com/v4")
    source.rights = RightsRecord(
        permission_status="authorized",
        commercial_use_allowed=True,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is False
    assert "expired" in reason.lower()


def test_eligibility_authorized_commercial_partner():
    """Explicitly authorized creator footage with commercial permissions must pass."""
    source = VideoSource(video_id="v5", title="GTA 6 Vice City", source_url="https://youtube.com/v5")
    source.rights = RightsRecord(
        permission_status="authorized",
        commercial_use_allowed=True,
        allowed_editing_scope="transformative_shorts",
        attribution_required=True,
        attribution_text="Courtesy of @ViceCityGamer",
    )
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is True
    assert "verified" in reason.lower()


def test_eligibility_own_gameplay():
    """Original own gameplay recordings must be fully eligible."""
    source = VideoSource(video_id="v6", title="Astro Rebel Original", source_url="https://youtube.com/v6")
    source.rights = RightsRecord(
        permission_status="own_gameplay",
        commercial_use_allowed=True,
        allowed_editing_scope="full",
    )
    is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
    assert is_eligible is True
