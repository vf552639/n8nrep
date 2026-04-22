from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_worker(async_api_client):
    r = await async_api_client.get("/api/health/worker")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


@pytest.mark.asyncio
async def test_health_serp(async_api_client):
    r = await async_api_client.get("/api/health/serp")
    assert r.status_code == 200
    body = r.json()
    assert "dataforseo" in body or "overall" in body
