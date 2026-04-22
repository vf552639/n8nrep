from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_list_sites_empty(async_api_client):
    r = await async_api_client.get("/api/sites/")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_site_happy(async_api_client):
    r = await async_api_client.post(
        "/api/sites/",
        json={
            "name": "API Test Site",
            "domain": "api-test.example.com",
            "country": "DE",
            "language": "De",
            "is_active": True,
        },
    )
    assert r.status_code == 200
    assert "id" in r.json()


@pytest.mark.asyncio
async def test_create_site_validation_error(async_api_client):
    r = await async_api_client.post("/api/sites/", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_site_404(async_api_client):
    r = await async_api_client.get(f"/api/sites/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_and_delete_site(async_api_client):
    cr = await async_api_client.post(
        "/api/sites/",
        json={
            "name": "Patch Me",
            "domain": "patch.example.com",
            "country": "FR",
            "language": "Fr",
            "is_active": True,
        },
    )
    assert cr.status_code == 200
    sid = cr.json()["id"]

    pr = await async_api_client.patch(f"/api/sites/{sid}", json={"name": "Patched Name"})
    assert pr.status_code == 200

    dr = await async_api_client.delete(f"/api/sites/{sid}")
    assert dr.status_code == 200

    r2 = await async_api_client.delete(f"/api/sites/{sid}")
    assert r2.status_code == 404
