from services.detector import inspect_url
import pytest


@pytest.mark.parametrize(
    ("url", "provider", "platform"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube", "YouTube"),
        ("https://www.instagram.com/p/example/", "instagram", "Instagram"),
        ("https://open.spotify.com/track/example", "spotify", "Spotify"),
        ("https://www.tiktok.com/@creator/video/123", "tiktok", "TikTok"),
        ("https://www.facebook.com/watch/?v=123", "facebook", "Facebook"),
    ],
)
def test_recognizes_supported_platforms(url, provider, platform):
    result = inspect_url(url)
    assert result["provider"] == provider
    assert result["platform"] == platform
    assert result["status"] == "recognized"


def test_unknown_host_is_not_supported():
    result = inspect_url("https://example.org/media")
    assert result["provider"] == "other"
    assert result["status"] == "unsupported"


@pytest.mark.parametrize("url", ["", "javascript:alert(1)", "not a url", "ftp://example.com/file"])
def test_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        inspect_url(url)
