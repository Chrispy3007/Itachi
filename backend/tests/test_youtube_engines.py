from unittest.mock import patch

import pytest

from services import youtube_engines


VIDEO_URL = "https://youtu.be/abcdefghijk"


def test_fallback_uses_youtubejs_after_generic_ytdlp_error():
    fallback = {
        "provider": "youtube",
        "status": "available",
        "engine": "youtubejs",
        "formats": [{"format_id": "youtubejs:18"}],
    }
    with patch("services.youtube_engines.inspect_youtube", side_effect=RuntimeError("extractor parser changed")), patch(
        "services.youtube_engines.inspect_youtubejs", return_value=fallback
    ) as alternate:
        result = youtube_engines.inspect_with_fallback(VIDEO_URL)
    alternate.assert_called_once_with(VIDEO_URL)
    assert result["engines_attempted"] == ["yt-dlp", "youtubejs"]
    assert result["formats"][0]["format_id"] == "youtubejs:18"


def test_fallback_does_not_retry_explicit_access_denial():
    with patch(
        "services.youtube_engines.inspect_youtube",
        side_effect=RuntimeError("Sign in to confirm you're not a bot"),
    ), patch("services.youtube_engines.inspect_youtubejs") as alternate:
        with pytest.raises(RuntimeError, match="Sign in"):
            youtube_engines.inspect_with_fallback(VIDEO_URL)
    alternate.assert_not_called()


def test_resolve_youtubejs_format_checks_current_catalog():
    catalog = {
        "provider": "youtube",
        "status": "available",
        "title": "Example",
        "webpage_url": VIDEO_URL,
        "formats": [{"format_id": "youtubejs:18", "ext": "mp4", "needs_merge": False}],
    }
    with patch("services.youtube_engines.inspect_youtubejs", return_value=catalog):
        result = youtube_engines.resolve_download_with_fallback(VIDEO_URL, "youtubejs:18")
    assert result["engine"] == "youtubejs"
    assert result["itag"] == "18"
    assert result["title"] == "Example"


def test_resolve_rejects_stale_youtubejs_format():
    catalog = {"formats": []}
    with patch("services.youtube_engines.inspect_youtubejs", return_value=catalog):
        with pytest.raises(ValueError, match="no longer available"):
            youtube_engines.resolve_download_with_fallback(VIDEO_URL, "youtubejs:999")
