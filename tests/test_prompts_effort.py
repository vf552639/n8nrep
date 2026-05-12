import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import os
    os.environ.setdefault("AUTH_DISABLED", "true")
    os.environ.setdefault("DESKTOP_MODE", "true")
    os.environ.setdefault("SQLITE_DB_PATH", "/tmp/p3_prompts.sqlite")
    from app.main import app
    return TestClient(app)


def test_prompt_update_accepts_effort_and_fast_mode(client):
    """PUT /api/prompts/{id} accepts effort and fast_mode."""
    resp = client.get("/api/prompts/")
    assert resp.status_code == 200
    prompts = resp.json()
    if not prompts:
        pytest.skip("No prompts in DB")

    prompt_id = prompts[0]["id"]

    resp = client.get(f"/api/prompts/{prompt_id}")
    assert resp.status_code == 200
    p = resp.json()

    update_body = {
        "system_prompt": p["system_prompt"],
        "user_prompt": p.get("user_prompt", ""),
        "model": p["model"],
        "max_tokens": p.get("max_tokens"),
        "max_tokens_enabled": p.get("max_tokens_enabled", False),
        "temperature": p.get("temperature", 0.7),
        "temperature_enabled": p.get("temperature_enabled", False),
        "frequency_penalty": p.get("frequency_penalty", 0.0),
        "frequency_penalty_enabled": p.get("frequency_penalty_enabled", False),
        "presence_penalty": p.get("presence_penalty", 0.0),
        "presence_penalty_enabled": p.get("presence_penalty_enabled", False),
        "top_p": p.get("top_p", 1.0),
        "top_p_enabled": p.get("top_p_enabled", False),
        "skip_in_pipeline": p.get("skip_in_pipeline", False),
        "effort": "medium",
        "fast_mode": True,
    }
    resp = client.put(f"/api/prompts/{prompt_id}", json=update_body)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["effort"] == "medium"
    assert updated["fast_mode"] is True


def test_prompt_detail_returns_effort_and_fast_mode(client):
    """GET /api/prompts/{id} returns effort and fast_mode in response."""
    resp = client.get("/api/prompts/")
    assert resp.status_code == 200
    prompts = resp.json()
    if not prompts:
        pytest.skip("No prompts in DB")

    prompt_id = prompts[0]["id"]
    resp = client.get(f"/api/prompts/{prompt_id}")
    assert resp.status_code == 200
    p = resp.json()
    assert "effort" in p
    assert "fast_mode" in p
