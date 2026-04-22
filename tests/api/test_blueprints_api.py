from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_blueprints_list(async_api_client):
    r = await async_api_client.get("/api/blueprints/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_blueprint_create_and_pages(async_api_client):
    r = await async_api_client.post(
        "/api/blueprints/",
        json={
            "name": "BP API",
            "slug": f"bp-api-{uuid.uuid4().hex[:12]}",
            "description": "d",
            "is_active": True,
        },
    )
    assert r.status_code == 200
    bid = r.json()["id"]

    pr = await async_api_client.get(f"/api/blueprints/{bid}/pages")
    assert pr.status_code == 200
    assert pr.json() == []

    pg = await async_api_client.post(
        f"/api/blueprints/{bid}/pages",
        json={
            "page_slug": "home",
            "page_title": "Home",
            "page_type": "article",
            "keyword_template": "{seed}",
            "filename": "home.html",
            "sort_order": 0,
            "pipeline_preset": "full",
        },
    )
    assert pg.status_code == 200
    page_id = pg.json()["id"]

    ur = await async_api_client.put(
        f"/api/blueprints/{bid}/pages/{page_id}",
        json={
            "page_slug": "home",
            "page_title": "Home Updated",
            "page_type": "article",
            "keyword_template": "{seed}",
            "filename": "home.html",
            "sort_order": 0,
            "pipeline_preset": "full",
        },
    )
    assert ur.status_code == 200

    dr = await async_api_client.delete(f"/api/blueprints/{bid}/pages/{page_id}")
    assert dr.status_code == 200


@pytest.mark.asyncio
async def test_create_blueprint_validation(async_api_client):
    r = await async_api_client.post("/api/blueprints/", json={})
    assert r.status_code == 422
