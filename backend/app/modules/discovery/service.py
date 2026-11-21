"""VANTYX Discovery & Rights Intelligence Service.

Manages GTA creator registry, autonomous source video discovery via official APIs
and public RSS/Atom feeds, commercial-use permissions, and pipeline eligibility gating.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.db.models.creator import Creator
from app.db.models.rights import RightsRecord
from app.db.models.source import VideoSource
from app.schemas.discovery import (
    CreatorCreate,
    CreatorUpdate,
    RightsRecordUpdate,
    VideoSourceCreate,
)


class DiscoveryService:
    """Service orchestrating creator registration, content ingestion, and rights gating."""

    is_active: bool = False

    async def list_approved_sources(self) -> List[Dict[str, Any]]:
        """Legacy interface helper for approved sources."""
        return []

    # ---------------- Creator Management ----------------

    @staticmethod
    async def create_creator(db: AsyncSession, data: CreatorCreate) -> Creator:
        """Register a new GTA creator channel."""
        creator = Creator(
            name=data.name,
            channel_id=data.channel_id,
            channel_handle=data.channel_handle,
            channel_url=data.channel_url or f"https://www.youtube.com/channel/{data.channel_id}",
            content_category=data.content_category,
            is_monitored=data.is_monitored,
            approval_status=data.approval_status,
            permission_tier=data.permission_tier,
            notes=data.notes,
        )
        db.add(creator)
        await db.commit()
        await db.refresh(creator)
        logger.info(f"Registered creator: {creator.name} ({creator.channel_id})")
        return creator

    @staticmethod
    async def list_creators(
        db: AsyncSession, monitored_only: bool = False, approved_only: bool = False
    ) -> List[Creator]:
        """List registered creators with optional filtering."""
        stmt = select(Creator).order_by(Creator.id.desc())
        if monitored_only:
            stmt = stmt.where(Creator.is_monitored.is_(True))
        if approved_only:
            stmt = stmt.where(Creator.approval_status == "approved")
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_creator(db: AsyncSession, creator_id: int) -> Optional[Creator]:
        """Retrieve creator by database ID."""
        return await db.get(Creator, creator_id)

    @staticmethod
    async def get_creator_by_channel_id(db: AsyncSession, channel_id: str) -> Optional[Creator]:
        """Retrieve creator by YouTube Channel ID."""
        stmt = select(Creator).where(Creator.channel_id == channel_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def update_creator(
        db: AsyncSession, creator_id: int, data: CreatorUpdate
    ) -> Optional[Creator]:
        """Update creator monitoring parameters and approval status."""
        creator = await db.get(Creator, creator_id)
        if not creator:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(creator, key, value)

        await db.commit()
        await db.refresh(creator)
        logger.info(f"Updated creator ID {creator_id}: {update_dict}")
        return creator

    @staticmethod
    async def delete_creator(db: AsyncSession, creator_id: int) -> bool:
        """Remove a creator and clean up associations."""
        creator = await db.get(Creator, creator_id)
        if not creator:
            return False
        await db.delete(creator)
        await db.commit()
        logger.info(f"Deleted creator ID {creator_id}")
        return True

    # ---------------- Video Discovery Engine ----------------

    @staticmethod
    async def discover_channel_videos(
        db: AsyncSession, creator: Creator
    ) -> Tuple[List[VideoSource], int]:
        """Discover latest gameplay videos from a creator channel.
        
        Uses YouTube Data API v3 if key is configured, or resilient public Atom feed.
        Returns:
            Tuple of (discovered_videos, duplicate_count)
        """
        raw_items: List[Dict[str, Any]] = []

        # 1. Try YouTube Data API if configured
        if settings.YOUTUBE_API_KEY:
            try:
                raw_items = await DiscoveryService._fetch_from_youtube_api(creator.channel_id)
            except Exception as exc:
                logger.warning(f"YouTube API failed for {creator.name}: {exc}. Falling back to Atom feed.")

        # 2. Resilient Fallback: YouTube Channel Public Atom Feed (zero credentials needed)
        if not raw_items:
            try:
                raw_items = await DiscoveryService._fetch_from_atom_feed(creator.channel_id)
            except Exception as exc:
                logger.error(f"Failed to fetch Atom feed for {creator.name} ({creator.channel_id}): {exc}")
                return [], 0

        new_sources: List[VideoSource] = []
        duplicate_count = 0

        for item in raw_items:
            vid = item["video_id"]
            # Check for duplicate
            stmt = select(VideoSource).where(VideoSource.video_id == vid)
            existing = (await db.execute(stmt)).scalars().first()
            if existing:
                duplicate_count += 1
                continue

            # Create video source record
            source = VideoSource(
                creator_id=creator.id,
                video_id=vid,
                title=item["title"],
                description=item.get("description", ""),
                duration_seconds=item.get("duration_seconds", 0),
                published_at=item.get("published_at"),
                thumbnail_url=item.get("thumbnail_url"),
                source_url=f"https://www.youtube.com/watch?v={vid}",
                discovery_method=item.get("method", "feed_ingest"),
                raw_metadata=item,
            )
            db.add(source)
            await db.flush()  # assign ID

            # Attach initial Rights Record based on creator's permission tier
            is_authorized = creator.permission_tier in ("own_content", "authorized_partner")
            is_commercial = is_authorized

            rights = RightsRecord(
                source_id=source.id,
                permission_status="authorized" if is_authorized else "pending",
                commercial_use_allowed=is_commercial,
                allowed_editing_scope="transformative_shorts",
                attribution_required=True,
                attribution_text=f"Original gameplay by {creator.name} ({creator.channel_url})",
                license_documentation=f"Inherited from Creator Tier: {creator.permission_tier}",
            )
            db.add(rights)
            new_sources.append(source)

        await db.commit()
        for s in new_sources:
            await db.refresh(s)

        logger.info(
            f"Discovery complete for {creator.name}: {len(new_sources)} new, {duplicate_count} skipped duplicates"
        )
        return new_sources, duplicate_count

    @staticmethod
    async def _fetch_from_atom_feed(channel_id: str) -> List[Dict[str, Any]]:
        """Fetch latest video items from YouTube's public XML Atom feed."""
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(feed_url, headers={"User-Agent": "VANTYX-Discovery/1.0"})
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} fetching feed for channel {channel_id}")

        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }

        items: List[Dict[str, Any]] = []
        for entry in root.findall("atom:entry", ns):
            vid_elem = entry.find("yt:videoId", ns)
            title_elem = entry.find("atom:title", ns)
            pub_elem = entry.find("atom:published", ns)
            media_group = entry.find("media:group", ns)

            video_id = vid_elem.text if vid_elem is not None else None
            title = title_elem.text if title_elem is not None else "Untitled GTA Gameplay"
            published_str = pub_elem.text if pub_elem is not None else None

            description = ""
            thumbnail_url = None
            if media_group is not None:
                desc_elem = media_group.find("media:description", ns)
                if desc_elem is not None and desc_elem.text:
                    description = desc_elem.text
                thumb_elem = media_group.find("media:thumbnail", ns)
                if thumb_elem is not None:
                    thumbnail_url = thumb_elem.get("url")

            published_at = None
            if published_str:
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            if video_id:
                items.append(
                    {
                        "video_id": video_id,
                        "title": title,
                        "description": description[:1000] if description else "",
                        "thumbnail_url": thumbnail_url or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                        "published_at": published_at,
                        "method": "feed_ingest",
                        "duration_seconds": 0,
                    }
                )
        return items

    @staticmethod
    async def _fetch_from_youtube_api(channel_id: str) -> List[Dict[str, Any]]:
        """Fetch latest videos using official YouTube Data API v3."""
        api_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": 10,
            "order": "date",
            "type": "video",
            "key": settings.YOUTUBE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"YouTube API returned HTTP {resp.status_code}")
            data = resp.json()

        items = []
        for item in data.get("items", []):
            id_info = item.get("id", {})
            vid = id_info.get("videoId")
            snippet = item.get("snippet", {})
            if vid:
                items.append(
                    {
                        "video_id": vid,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", "")[:1000],
                        "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                        "published_at": snippet.get("publishedAt"),
                        "method": "youtube_api",
                        "duration_seconds": 0,
                    }
                )
        return items

    @staticmethod
    async def run_discovery_cycle(db: AsyncSession) -> Dict[str, Any]:
        """Execute a full discovery sweep across all monitored, approved creators."""
        creators = await DiscoveryService.list_creators(db, monitored_only=True, approved_only=True)
        total_discovered = 0
        total_skipped = 0
        errors: List[str] = []

        for creator in creators:
            try:
                new_sources, skipped = await DiscoveryService.discover_channel_videos(db, creator)
                total_discovered += len(new_sources)
                total_skipped += skipped
            except Exception as exc:
                err_msg = f"Error discovering {creator.name}: {exc}"
                logger.error(err_msg)
                errors.append(err_msg)

        return {
            "channels_polled": len(creators),
            "videos_discovered": total_discovered,
            "duplicates_skipped": total_skipped,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc),
        }

    # ---------------- Source & Rights Management ----------------

    @staticmethod
    async def list_sources(
        db: AsyncSession, creator_id: Optional[int] = None, eligible_only: bool = False
    ) -> List[VideoSource]:
        """List video sources with optional creator and eligibility filters."""
        stmt = (
            select(VideoSource)
            .options(selectinload(VideoSource.rights), selectinload(VideoSource.creator))
            .order_by(VideoSource.id.desc())
        )
        if creator_id is not None:
            stmt = stmt.where(VideoSource.creator_id == creator_id)

        result = await db.execute(stmt)
        sources = list(result.scalars().all())

        if eligible_only:
            eligible_sources = []
            for src in sources:
                is_eligible, _ = DiscoveryService.evaluate_eligibility(src)
                if is_eligible:
                    eligible_sources.append(src)
            return eligible_sources

        return sources

    @staticmethod
    async def get_source(db: AsyncSession, source_id: int) -> Optional[VideoSource]:
        """Retrieve video source by database ID."""
        stmt = (
            select(VideoSource)
            .where(VideoSource.id == source_id)
            .options(selectinload(VideoSource.rights), selectinload(VideoSource.creator))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def ingest_manual_source(db: AsyncSession, data: VideoSourceCreate) -> VideoSource:
        """Manually register an owned recording or verified partner video."""
        # Check duplicate
        stmt = select(VideoSource).where(VideoSource.video_id == data.video_id)
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise ValueError(f"Video ID '{data.video_id}' is already registered in VANTYX catalog.")

        source = VideoSource(
            creator_id=data.creator_id,
            video_id=data.video_id,
            title=data.title,
            description=data.description,
            duration_seconds=data.duration_seconds,
            published_at=data.published_at or datetime.now(timezone.utc),
            thumbnail_url=data.thumbnail_url or f"https://i.ytimg.com/vi/{data.video_id}/hqdefault.jpg",
            source_url=data.source_url,
            discovery_method=data.discovery_method,
        )
        db.add(source)
        await db.flush()

        # Rights record
        permission_status = "own_gameplay" if data.is_own_gameplay else "authorized"
        rights = RightsRecord(
            source_id=source.id,
            permission_status=permission_status,
            commercial_use_allowed=True,
            allowed_editing_scope="full" if data.is_own_gameplay else "transformative_shorts",
            attribution_required=not data.is_own_gameplay,
            attribution_text=data.attribution_text or ("Own Original Gameplay" if data.is_own_gameplay else None),
            license_documentation="Direct Manual Import Verification",
            verified_by="Operator",
            verified_at=datetime.now(timezone.utc),
        )
        db.add(rights)
        await db.commit()
        fresh_source = await DiscoveryService.get_source(db, source.id)
        return fresh_source or source

    @staticmethod
    async def update_source_rights(
        db: AsyncSession, source_id: int, data: RightsRecordUpdate
    ) -> Optional[RightsRecord]:
        """Update permission status and commercial authorization for a source."""
        stmt = select(RightsRecord).where(RightsRecord.source_id == source_id)
        result = await db.execute(stmt)
        rights = result.scalars().first()

        if not rights:
            rights = RightsRecord(source_id=source_id)
            db.add(rights)

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(rights, key, value)

        rights.verified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(rights)
        logger.info(f"Updated rights for source {source_id}: status={rights.permission_status}, commercial={rights.commercial_use_allowed}")
        return rights

    # ---------------- Eligibility Validation Gate ----------------

    @staticmethod
    def evaluate_eligibility(source: VideoSource) -> Tuple[bool, str]:
        """Pure synchronous validation of source eligibility according to commercial guidelines."""
        if not source.rights:
            return False, "No rights management record found for this source"

        r = source.rights

        # 1. Permission status check
        if r.permission_status not in ("authorized", "own_gameplay"):
            return False, f"Permission status is '{r.permission_status}', requires 'authorized' or 'own_gameplay'"

        # 2. Commercial use check
        if not r.commercial_use_allowed:
            return False, "Commercial-use authorization is not granted for this media"

        # 3. Expiration check
        if r.expires_at:
            now = datetime.now(timezone.utc)
            exp = r.expires_at if r.expires_at.tzinfo else r.expires_at.replace(tzinfo=timezone.utc)
            if now > exp:
                return False, f"Usage permission expired on {r.expires_at.isoformat()}"

        # 4. Editing scope check
        if r.allowed_editing_scope == "restricted":
            return False, "Editing scope is restricted; transformative vertical shorts not permitted"

        return True, "Commercial and transformative rights verified. Eligible for production pipeline."

    @staticmethod
    async def check_source_eligibility(db: AsyncSession, source_id: int) -> Tuple[bool, str, VideoSource]:
        """Retrieve source and execute legal eligibility check."""
        source = await DiscoveryService.get_source(db, source_id)
        if not source:
            raise ValueError(f"Video source ID {source_id} not found")
        is_eligible, reason = DiscoveryService.evaluate_eligibility(source)
        return is_eligible, reason, source
