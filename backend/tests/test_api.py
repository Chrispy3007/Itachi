from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
        "message": "Only combined formats are listed.",
    }
    with patch("main.inspect_youtube", return_value=sample):
        response = client.post("/api/youtube/inspect", json={"url": "https://youtu.be/abcdefghijk"})
    assert response.status_code == 200
    assert response.json()["formats"][0]["format_id"] == "18"


def test_youtube_inspect_rejects_non_youtube_url():
    response = client.post("/api/youtube/inspect", json={"url": "https://example.org/video"})
    assert response.status_code == 422


def test_youtube_download_rejects_unlisted_format():
    with patch("main.resolve_download", side_effect=ValueError("That format is not available.")):
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
