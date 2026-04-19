import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_root_ok(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
