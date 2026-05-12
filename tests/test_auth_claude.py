import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import os
    os.environ.setdefault("AUTH_DISABLED", "true")
    os.environ.setdefault("DESKTOP_MODE", "true")
    os.environ.setdefault("SQLITE_DB_PATH", "/tmp/p3_auth.sqlite")
    from app.main import app
    return TestClient(app)


def test_claude_login_returns_url(client):
    """POST /api/auth/claude/login spawns subprocess and returns OAuth URL."""
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = [
        "Opening browser...\n",
        "Login URL: https://claude.ai/oauth/authorize?code=abc123\n",
        "",
    ]

    with patch("app.api.auth.subprocess.Popen", return_value=mock_proc):
        resp = client.post("/api/auth/claude/login")

    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert "claude.ai" in data["url"]


def test_claude_login_handles_missing_cli(client):
    """Returns error dict when claude CLI not found."""
    with patch("app.api.auth.subprocess.Popen", side_effect=FileNotFoundError):
        resp = client.post("/api/auth/claude/login")

    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_claude_status_not_logged_in(client):
    """GET /api/auth/claude/status returns logged_in=False when no credentials."""
    with patch("app.api.auth.Path") as mock_path_cls:
        fake_path = MagicMock()
        fake_path.exists.return_value = False
        mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value = fake_path

        resp = client.get("/api/auth/claude/status")

    assert resp.status_code == 200
    data = resp.json()
    assert "logged_in" in data


def test_claude_status_logged_in(client, tmp_path):
    """GET /api/auth/claude/status returns logged_in=True when credentials exist."""
    creds = {
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-test",
            "userEmail": "user@example.com",
        }
    }

    with patch("app.api.auth.Path") as mock_path_cls:
        instance = MagicMock()
        instance.exists.return_value = True
        instance.read_text.return_value = json.dumps(creds)
        mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value = instance

        resp = client.get("/api/auth/claude/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["logged_in"] is True
    assert data["email"] == "user@example.com"
