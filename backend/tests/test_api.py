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


def test_github_pages_origin_is_allowed():
    response = client.options(
        "/api/inspect",
        headers={
            "Origin": "https://chrispy3007.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://chrispy3007.github.io"
