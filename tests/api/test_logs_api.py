from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_logs_list(async_api_client):
    r = await async_api_client.get("/api/logs/")
    assert r.status_code == 200
    body = r.json()
    assert "logs" in body
