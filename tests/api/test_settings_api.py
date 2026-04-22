from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_settings_get_put_uses_temp_env(async_api_client, monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("FOO=bar\nOPENROUTER_API_KEY=sk-test-key-1234567890\n")

    import app.api.settings_api as sa

    monkeypatch.setattr(sa, "get_env_path", lambda: str(env_path))

    gr = await async_api_client.get("/api/settings/")
    assert gr.status_code == 200
    data = gr.json()
    assert data.get("FOO") == "bar"
    assert "OPENROUTER_API_KEY" in data

    pr = await async_api_client.put(
        "/api/settings/",
        json={"FOO": "baz", "SEQUENTIAL_MODE": "true"},
    )
    assert pr.status_code == 200
    assert "FOO=baz" in env_path.read_text() or "baz" in env_path.read_text()
