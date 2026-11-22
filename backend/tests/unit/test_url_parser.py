"""Unit tests for YouTube URL Normalization & Validation."""

import pytest
from app.modules.discovery.url_parser import (
    canonicalize_youtube_url,
    parse_youtube_url,
    validate_and_normalize_youtube_url,
)


class TestYouTubeUrlParser:
    """Test suite for parse_youtube_url and canonicalize_youtube_url."""

    # 1. Standard Desktop URLs
    def test_standard_desktop_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        vid = parse_youtube_url(url)
        assert vid == "dQw4w9WgXcQ"
        assert canonicalize_youtube_url(vid) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_standard_desktop_url_no_subdomain(self):
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_standard_url_http(self):
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 2. Shortened youtu.be URLs
    def test_shortened_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        vid = parse_youtube_url(url)
        assert vid == "dQw4w9WgXcQ"
        assert canonicalize_youtube_url(vid) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_shortened_url_www(self):
        url = "https://www.youtu.be/dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 3. YouTube Shorts URLs
    def test_shorts_url(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        vid = parse_youtube_url(url)
        assert vid == "dQw4w9WgXcQ"
        assert canonicalize_youtube_url(vid) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_shorts_url_no_subdomain(self):
        url = "https://youtube.com/shorts/dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 4. Embedded Video URLs
    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        vid = parse_youtube_url(url)
        assert vid == "dQw4w9WgXcQ"

    def test_legacy_v_url(self):
        url = "https://www.youtube.com/v/dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 5. Mobile URLs & Alternate subdomains
    def test_mobile_youtube_url(self):
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_gaming_youtube_url(self):
        url = "https://gaming.youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 6. Additional Query Parameters & Tracking Fragments
    def test_url_with_multiple_query_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL12345&feature=shared&si=abcdef"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_shortened_url_with_tracking_params(self):
        url = "https://youtu.be/dQw4w9WgXcQ?si=abcdef123456&t=15"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_shorts_url_with_query_params(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 7. Whitespace Handling
    def test_url_with_leading_and_trailing_whitespace(self):
        url = "   https://youtu.be/dQw4w9WgXcQ \n\t "
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    # 8. Invalid and Unsupported Hosts
    @pytest.mark.parametrize(
        "unsupported_url",
        [
            "https://vimeo.com/123456789",
            "https://dailymotion.com/video/x7abcde",
            "https://evil-youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com.attacker.com/watch?v=dQw4w9WgXcQ",
            "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
            "https://twitch.tv/videos/1234567890",
            "https://tiktok.com/@user/video/12345678901",
        ],
    )
    def test_unsupported_hosts_rejected(self, unsupported_url):
        assert parse_youtube_url(unsupported_url) is None

    # 9. Invalid Video ID formats
    @pytest.mark.parametrize(
        "invalid_id_url",
        [
            "https://www.youtube.com/watch?v=short",          # Too short (5 chars)
            "https://www.youtube.com/watch?v=waytoolongvideoid123",  # Too long (21 chars)
            "https://www.youtube.com/watch?v=dQw4w9WgXc!",    # Invalid char '!'
            "https://www.youtube.com/watch?v=dQw4w9WgXc$",    # Invalid char '$'
            "https://www.youtube.com/watch?v=",               # Empty v param
            "https://www.youtube.com/watch",                  # No query
            "https://youtu.be/",                              # No path
            "https://www.youtube.com/shorts/",                # No shorts ID
            "https://www.youtube.com/embed/",                 # No embed ID
        ],
    )
    def test_invalid_video_ids_rejected(self, invalid_id_url):
        assert parse_youtube_url(invalid_id_url) is None

    # 10. Malformed or Non-URL Inputs
    @pytest.mark.parametrize(
        "malformed_input",
        [
            "",
            "   ",
            None,
            "not_a_url",
            "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
            "file:///C:/videos/test.mp4",
            "javascript:alert(1)",
        ],
    )
    def test_malformed_inputs_rejected(self, malformed_input):
        assert parse_youtube_url(malformed_input) is None

    # 11. Detailed Validator Helper
    def test_validate_and_normalize_helper(self):
        valid, vid, canonical, err = validate_and_normalize_youtube_url(
            "https://youtu.be/dQw4w9WgXcQ?si=test"
        )
        assert valid is True
        assert vid == "dQw4w9WgXcQ"
        assert canonical == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert err is None

        valid_err, vid_err, canonical_err, err_msg = validate_and_normalize_youtube_url(
            "https://vimeo.com/12345"
        )
        assert valid_err is False
        assert vid_err is None
        assert "Unsupported host" in err_msg
