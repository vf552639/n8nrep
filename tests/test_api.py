from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_api_settings_auth():
    # Force settings so the dependency triggers
    settings.API_KEY = "test_secret_key"

    # Without X-API-Key, should fail because we added deps
    response = client.get("/api/settings/")
    assert response.status_code == 403

    # Or if your auth allows local bypass, verify accordingly.
    # Let's test with a fake key if it's protected
    headers = {"X-API-Key": "invalid"}
    response = client.get("/api/settings/", headers=headers)
    assert response.status_code == 403


def test_dashboard_stats_auth_enforced():
    settings.API_KEY = "test_secret_key"
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 403
