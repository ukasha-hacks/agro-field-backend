import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FRONTEND_ORIGIN = "https://agrofields.vercel.app"


@pytest.mark.parametrize("origin", [FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"])
def test_frontend_can_read_the_catalog(monkeypatch, origin):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/locations", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert len(response.json()) == 4


def test_frontend_can_preflight_a_json_submission(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    response = TestClient(create_app()).options(
        "/api/v1/rotation-comparisons",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_other_origins_are_not_allowed(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    response = TestClient(create_app()).options(
        "/api/v1/rotation-comparisons",
        headers={
            "Origin": "https://another-site.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_configured_origins_replace_defaults_and_accept_a_trailing_slash(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " https://preview.example/ , ")
    settings = Settings.from_environment()
    assert settings.cors_origins == ("https://preview.example",)

