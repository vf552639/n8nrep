import os
os.environ["DESKTOP_MODE"] = "true"
os.environ["SQLITE_DB_PATH"] = "/tmp/test_health.sqlite"
os.environ["AUTH_DISABLED"] = "true"

import pytest
from fastapi.testclient import TestClient


def test_worker_health_in_desktop_mode():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/api/health/worker")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "active_projects" in body
