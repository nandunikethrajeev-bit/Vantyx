"""VANTYX YouTube Metadata Resolution Providers.

Resolves real video title, author, thumbnail, and metadata using official, compliant APIs:
- YouTube oEmbed API (official public embed endpoint, requires no API key or scraping).
- YouTube Data API v3 (when configured with YOUTUBE_API_KEY).
- Local / fallback provider for offline and synthetic media.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger


class MetadataProviderInterface(ABC):
    """Abstract interface defining the video metadata resolution boundary."""

    _test_overrides: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_test_metadata(cls, video_id: str, data: Dict[str, Any]) -> None:
        """Register controlled test metadata overrides for synthetic verification."""
        cls._test_overrides[video_id] = data

    @classmethod
    def clear_test_metadata(cls) -> None:
        """Clear test metadata overrides."""
        cls._test_overrides.clear()

    @abstractmethod
    async def resolve_metadata(self, video_id: str, canonical_url: str) -> Dict[str, Any]:
        """Resolve public video metadata for a given canonical YouTube URL."""
        pass


class YouTubeOEmbedMetadataProvider(MetadataProviderInterface):
    """Official YouTube oEmbed Provider.
    
    Uses https://www.youtube.com/oembed?url={canonical_url}&format=json.
    Standardized, free, requires no API credentials, and operates without scraping.
    """

    async def resolve_metadata(self, video_id: str, canonical_url: str) -> Dict[str, Any]:
        # Check registered test overrides
        if video_id in self._test_overrides:
            override = self._test_overrides[video_id]
            return {
                "resolved": True,
                "title": override.get("title") or f"YouTube Video {video_id}",
                "author_name": override.get("author_name"),
                "author_url": override.get("author_url"),
                "channel_id": override.get("channel_id"),
                "thumbnail_url": override.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "provider": "test_override",
                "raw_data": override,
            }
        oembed_url = "https://www.youtube.com/oembed"
        params = {"url": canonical_url, "format": "json"}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(oembed_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    channel_id = None
                    author_url = data.get("author_url")
                    if author_url and "/channel/" in author_url:
                        channel_id = author_url.split("/channel/")[-1].split("/")[0]
                    if channel_id and "channel_id" not in data:
                        data["channel_id"] = channel_id

                    return {
                        "resolved": True,
                        "title": data.get("title") or f"YouTube Video {video_id}",
                        "author_name": data.get("author_name"),
                        "author_url": author_url,
                        "channel_id": channel_id,
                        "thumbnail_url": data.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                        "provider": "youtube_oembed",
                        "raw_data": data,
                    }
        except Exception as exc:
            logger.debug(f"YouTube oEmbed metadata lookup for {video_id} skipped: {exc}")

        return {
            "resolved": False,
            "title": f"YouTube Video {video_id}",
            "author_name": None,
            "author_url": None,
            "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "provider": "fallback",
        }


class YouTubeDataApiMetadataProvider(MetadataProviderInterface):
    """YouTube Data API v3 Provider for extended snippet/contentDetails."""

    async def resolve_metadata(self, video_id: str, canonical_url: str) -> Dict[str, Any]:
        if not settings.YOUTUBE_API_KEY:
            return {"resolved": False, "provider": "youtube_api_disabled"}

        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails",
            "id": video_id,
            "key": settings.YOUTUBE_API_KEY,
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    if items:
                        snippet = items[0].get("snippet", {})
                        thumbnails = snippet.get("thumbnails", {})
                        thumb = (
                            thumbnails.get("maxres", {}).get("url")
                            or thumbnails.get("high", {}).get("url")
                            or thumbnails.get("default", {}).get("url")
                        )
                        return {
                            "resolved": True,
                            "title": snippet.get("title") or f"YouTube Video {video_id}",
                            "description": snippet.get("description", ""),
                            "author_name": snippet.get("channelTitle"),
                            "channel_id": snippet.get("channelId"),
                            "author_url": f"https://www.youtube.com/channel/{snippet.get('channelId')}" if snippet.get("channelId") else None,
                            "thumbnail_url": thumb or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                            "published_at": snippet.get("publishedAt"),
                            "provider": "youtube_data_api_v3",
                            "raw_data": items[0],
                        }
        except Exception as exc:
            logger.warning(f"YouTube Data API metadata resolution failed for {video_id}: {exc}")

        return {"resolved": False, "provider": "youtube_api_unreachable"}


class CompositeMetadataProvider(MetadataProviderInterface):
    """Chains official YouTube Data API v3 -> YouTube oEmbed -> default fallback."""

    def __init__(self) -> None:
        self.data_api = YouTubeDataApiMetadataProvider()
        self.oembed = YouTubeOEmbedMetadataProvider()

    async def resolve_metadata(self, video_id: str, canonical_url: str) -> Dict[str, Any]:
        if settings.YOUTUBE_API_KEY:
            res = await self.data_api.resolve_metadata(video_id, canonical_url)
            if res.get("resolved"):
                return res

        res = await self.oembed.resolve_metadata(video_id, canonical_url)
        if res.get("resolved"):
            return res

        return {
            "resolved": False,
            "title": f"YouTube Video {video_id}",
            "author_name": None,
            "author_url": None,
            "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "provider": "deterministic_fallback",
        }


def get_metadata_provider() -> MetadataProviderInterface:
    """Retrieve default metadata resolution provider."""
    return CompositeMetadataProvider()
