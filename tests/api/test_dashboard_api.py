from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_dashboard_stats(async_api_client):
    r = await async_api_client.get("/api/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    assert "tasks" in body
    assert "sites" in body


@pytest.mark.asyncio
async def test_dashboard_queue(async_api_client):
    r = await async_api_client.get("/api/dashboard/queue")
    assert r.status_code == 200
    body = r.json()
    assert "celery_workers_online" in body
