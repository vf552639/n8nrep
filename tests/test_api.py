from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_api_settings_auth(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", False, raising=False)
    monkeypatch.setattr(settings, "API_KEY", "test_secret_key", raising=False)

    # Without X-API-Key, should fail because we added deps
    response = client.get("/api/settings/")
    assert response.status_code == 403

    # Or if your auth allows local bypass, verify accordingly.
    # Let's test with a fake key if it's protected
    headers = {"X-API-Key": "invalid"}
    response = client.get("/api/settings/", headers=headers)
    assert response.status_code == 403


def test_dashboard_stats_auth_enforced(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", False, raising=False)
    monkeypatch.setattr(settings, "API_KEY", "test_secret_key", raising=False)
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 403
