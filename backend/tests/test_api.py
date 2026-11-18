from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.youtube import inspect_youtube, resolve_download


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    components = response.json()["components"]
    assert components["yt_dlp"]["available"] is True
    assert "deno" in components
    assert "ffmpeg" in components


def test_provider_catalog_contains_expected_platforms():
    response = client.get("/api/providers")
    assert response.status_code == 200
    ids = {provider["id"] for provider in response.json()}
    assert {"youtube", "instagram", "spotify", "tiktok", "facebook"} <= ids


def test_inspect_recognizes_youtube_link():
    response = client.post("/api/inspect", json={"url": "https://youtu.be/abcdefghijk"})
    assert response.status_code == 200
    assert response.json()["provider"] == "youtube"
    assert response.json()["status"] == "recognized"


def test_inspect_rejects_unsupported_provider():
    response = client.post("/api/inspect", json={"url": "https://example.org/video"})
    assert response.status_code == 422


def test_youtube_inspect_returns_format_catalog():
    sample = {
        "provider": "youtube",
        "status": "available",
        "title": "Example video",
        "formats": [{"format_id": "18", "ext": "mp4", "resolution": "360p", "filesize": 1234}],
        "message": "Available video formats.",
    }
    with patch("main.inspect_with_fallback", return_value=sample):
        response = client.post("/api/youtube/inspect", json={"url": "https://youtu.be/abcdefghijk"})
    assert response.status_code == 200
    assert response.json()["formats"][0]["format_id"] == "18"


def test_inspect_includes_adaptive_video_only_formats():
    info = {
        "id": "abcdefghijk",
        "title": "Example video",
        "formats": [
            {"format_id": "137", "ext": "mp4", "height": 1080, "fps": 30, "vcodec": "avc1", "acodec": "none", "protocol": "https", "filesize": 5000},
            {"format_id": "18", "ext": "mp4", "height": 360, "vcodec": "avc1", "acodec": "mp4a", "protocol": "https", "filesize": 1000},
            {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "protocol": "https"},
            {"format_id": "999", "ext": "mp4", "height": 2160, "vcodec": "av01", "acodec": "none", "protocol": "https", "has_drm": True},
        ],
    }
    with patch("services.youtube._extract_info", return_value=info), patch("services.youtube.validate_youtube_url", return_value="https://youtu.be/abcdefghijk"):
        result = inspect_youtube("https://youtu.be/abcdefghijk")
    assert [item["format_id"] for item in result["formats"]] == ["137", "18"]
    assert result["formats"][0]["needs_merge"] is True
    assert result["formats"][0]["ext"] == "mkv"
    assert result["formats"][1]["needs_merge"] is False


def test_resolve_adaptive_format_pairs_best_audio():
    info = {
        "id": "abcdefghijk",
        "title": "Example video",
        "formats": [
            {"format_id": "137", "ext": "mp4", "height": 1080, "vcodec": "avc1", "acodec": "none", "protocol": "https"},
        ],
    }
    with patch("services.youtube._extract_info", return_value=info), patch("services.youtube.validate_youtube_url", return_value="https://youtu.be/abcdefghijk"):
        resolved = resolve_download("https://youtu.be/abcdefghijk", "137")
    assert resolved["format_selector"] == "137+bestaudio/best"
    assert resolved["format"]["needs_merge"] is True


def test_youtube_inspect_rejects_non_youtube_url():
    response = client.post("/api/youtube/inspect", json={"url": "https://example.org/video"})
    assert response.status_code == 422


def test_youtube_download_rejects_unlisted_format():
    with patch("main.resolve_download_with_fallback", side_effect=ValueError("That format is not available.")):
        response = client.post(
            "/api/youtube/download",
            json={"url": "https://youtu.be/abcdefghijk", "format_id": "999"},
        )
    assert response.status_code == 422


def test_github_pages_origin_is_allowed():
    response = client.options(
        "/api/youtube/inspect",
        headers={
            "Origin": "https://chrispy3007.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://chrispy3007.github.io"



def test_youtube_job_endpoints_report_missing_job():
    response = client.get("/api/youtube/jobs/not-a-real-job")
    assert response.status_code == 404


def test_youtube_job_creation_rejects_invalid_format():
    response = client.post(
        "/api/youtube/jobs",
        json={"url": "https://youtu.be/abcdefghijk", "format_id": ""},
    )
    assert response.status_code == 422
