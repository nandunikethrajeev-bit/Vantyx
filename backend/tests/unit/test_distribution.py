"""Unit tests for Distribution service, timezone conversions, and metadata synthesis."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.db.models.creator import Creator
from app.db.models.rights import RightsRecord
from app.db.models.selection import CandidateClip
from app.db.models.source import VideoSource
from app.modules.distribution.service import DistributionService, TimezoneHelper


def test_timezone_conversion_to_utc():
    """Verify Asia/Kolkata (UTC+05:30) slot time converts accurately to UTC."""
    # 09:00 IST -> 03:30 UTC
    utc_dt = TimezoneHelper.slot_to_utc("2026-12-01", "09:00")
    assert utc_dt.year == 2026
    assert utc_dt.month == 12
    assert utc_dt.day == 1
    assert utc_dt.hour == 3
    assert utc_dt.minute == 30
    assert utc_dt.tzinfo == timezone.utc

    # 13:00 IST -> 07:30 UTC
    utc_dt_13 = TimezoneHelper.slot_to_utc("2026-12-01", "13:00")
    assert utc_dt_13.hour == 7
    assert utc_dt_13.minute == 30

    # 21:00 IST -> 15:30 UTC
    utc_dt_21 = TimezoneHelper.slot_to_utc("2026-12-01", "21:00")
    assert utc_dt_21.hour == 15
    assert utc_dt_21.minute == 30


def test_utc_to_kolkata_formatting():
    """Verify formatting UTC datetime into Asia/Kolkata localized string."""
    utc_dt = datetime(2026, 12, 1, 3, 30, tzinfo=timezone.utc)
    formatted = TimezoneHelper.utc_to_kolkata_str(utc_dt)
    assert "2026-12-01 09:00 (Asia/Kolkata)" in formatted


def test_metadata_synthesis_with_creator_attribution():
    """Verify title, tags, and mandatory creator attribution text in description."""
    creator = Creator(id=1, name="Vice City Stunts", channel_id="UC123")
    source = VideoSource(
        id=10,
        creator=creator,
        video_id="stunt_vid",
        title="Epic Helicopter Jump",
        source_url="https://youtube.com/watch?v=stunt_vid",
    )
    rights = RightsRecord(
        id=5,
        source_id=10,
        permission_status="authorized",
        commercial_use_allowed=True,
        attribution_required=True,
        attribution_text="Footage provided by Vice City Stunts (@ViceCityStunts).",
    )
    source.rights = rights

    candidate = CandidateClip(
        id=1,
        source_id=10,
        start_time=10.0,
        end_time=50.0,
        duration_seconds=40.0,
        title_suggestion="GTA 6 Insane Canal Helicopter Jump",
        rationale="High hook velocity.",
    )

    title, desc, tags = DistributionService.build_publication_metadata(candidate, source)
    assert "#Shorts" in title
    assert len(title) <= 100
    assert "Vice City Stunts" in desc
    assert "Attribution: Footage provided by Vice City Stunts" in desc
    assert "GTA 6" in tags
    assert "#AstroRebel" in desc
