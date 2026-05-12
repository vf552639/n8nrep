import json
from fastapi.testclient import TestClient


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_OAUTH_DIR", str(tmp_path / ".codex"))
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DESKTOP_MODE", "true")
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "db.sqlite"))
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    from app.main import app
    return TestClient(app)


def test_codex_status_logged_out(tmp_path, monkeypatch):
    c = _client(monkeypatch, tmp_path)
    r = c.get("/api/auth/codex/status")
    assert r.status_code == 200
    assert r.json() == {"logged_in": False, "method": None, "account_id": None}


def test_codex_status_logged_in(tmp_path, monkeypatch):
    oauth = tmp_path / ".codex"
    oauth.mkdir()
    (oauth / "auth.json").write_text(
        json.dumps({"tokens": {"access_token": "tok", "account_id": "acc_42"}})
    )
    c = _client(monkeypatch, tmp_path)
    r = c.get("/api/auth/codex/status")
    assert r.status_code == 200
    body = r.json()
    assert body == {"logged_in": True, "method": "oauth", "account_id": "acc_42"}


def test_codex_logout_removes_auth_file(tmp_path, monkeypatch):
    oauth = tmp_path / ".codex"
    oauth.mkdir()
    auth_file = oauth / "auth.json"
    auth_file.write_text("{}")
    c = _client(monkeypatch, tmp_path)
    r = c.post("/api/auth/codex/logout")
    assert r.status_code == 200
    assert r.json() == {"logged_out": True}
    assert not auth_file.exists()
