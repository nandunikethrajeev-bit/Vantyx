"""VANTYX YouTube URL Normalizer & Validator.

Extracts, validates, and canonicalizes YouTube video IDs from diverse URL formats:
- Standard desktop: https://www.youtube.com/watch?v=VIDEO_ID
- Shortened: https://youtu.be/VIDEO_ID
- Shorts: https://www.youtube.com/shorts/VIDEO_ID
- Embed: https://www.youtube.com/embed/VIDEO_ID
- Mobile: https://m.youtube.com/watch?v=VIDEO_ID
- Additional query parameters and timestamp fragments.
"""

import re
from typing import Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse

# Standard YouTube 11-character base64url video ID
YOUTUBE_VIDEO_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Permitted official YouTube domain names (strictly enforce, no subdomains/lookalikes)
ALLOWED_YOUTUBE_HOSTS: Set[str] = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "gaming.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def parse_youtube_url(url: Optional[str]) -> Optional[str]:
    """Extract and validate the 11-character YouTube video ID from a URL.
    
    Returns:
        11-character video ID string if valid and supported, otherwise None.
    """
    if not url or not isinstance(url, str):
        return None

    cleaned_url = url.strip()
    if not cleaned_url:
        return None

    try:
        parsed = urlparse(cleaned_url)
    except Exception:
        return None

    # Enforce safe schemes
    if parsed.scheme not in ("http", "https"):
        return None

    hostname = (parsed.hostname or "").lower()
    if hostname not in ALLOWED_YOUTUBE_HOSTS:
        return None

    video_id: Optional[str] = None

    if hostname in ("youtu.be", "www.youtu.be"):
        # Path format: /VIDEO_ID
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            video_id = path_parts[0]
    else:
        # Host is *.youtube.com
        path = parsed.path.rstrip("/")
        if path == "/watch":
            # Query parameter: ?v=VIDEO_ID
            qs = parse_qs(parsed.query)
            v_param = qs.get("v")
            if v_param and len(v_param) > 0:
                video_id = v_param[0]
        elif path.startswith("/shorts/"):
            # Path format: /shorts/VIDEO_ID
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] == "shorts":
                video_id = parts[1]
        elif path.startswith("/embed/"):
            # Path format: /embed/VIDEO_ID
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] == "embed":
                video_id = parts[1]
        elif path.startswith("/v/"):
            # Legacy path format: /v/VIDEO_ID
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] == "v":
                video_id = parts[1]

    if not video_id:
        return None

    # Validate against strict 11-character base64url regex
    if not YOUTUBE_VIDEO_ID_REGEX.match(video_id):
        return None

    return video_id


def canonicalize_youtube_url(video_id: str) -> str:
    """Format an 11-character YouTube video ID into canonical watch URL."""
    if not YOUTUBE_VIDEO_ID_REGEX.match(video_id):
        raise ValueError(f"Invalid YouTube video ID format: '{video_id}'")
    return f"https://www.youtube.com/watch?v={video_id}"


def validate_and_normalize_youtube_url(url: Optional[str]) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """Validate a URL and return a tuple of (is_valid, video_id, canonical_url, error_message)."""
    if not url or not isinstance(url, str) or not url.strip():
        return False, None, None, "URL cannot be empty."

    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
    except Exception as exc:
        return False, None, None, f"Malformed URL syntax: {exc}"

    if parsed.scheme not in ("http", "https"):
        return False, None, None, f"Unsupported URL protocol '{parsed.scheme}'. Only http and https are allowed."

    hostname = (parsed.hostname or "").lower()
    if hostname not in ALLOWED_YOUTUBE_HOSTS:
        return False, None, None, f"Unsupported host '{hostname}'. Only official YouTube domains are accepted."

    video_id = parse_youtube_url(cleaned)
    if not video_id:
        return False, None, None, "Could not extract valid 11-character YouTube video ID from URL."

    canonical = canonicalize_youtube_url(video_id)
    return True, video_id, canonical, None
