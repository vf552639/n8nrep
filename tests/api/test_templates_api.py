from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_templates_list(async_api_client):
    r = await async_api_client.get("/api/templates/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_template_crud(async_api_client):
    r = await async_api_client.post(
        "/api/templates/",
        json={
            "name": "TPL API",
            "html_template": "<html><body>{{content}}</body></html>",
            "is_active": True,
        },
    )
    assert r.status_code == 200
    tid = r.json()["id"]

    gr = await async_api_client.get(f"/api/templates/{tid}")
    assert gr.status_code == 200
    assert gr.json()["name"] == "TPL API"

    ur = await async_api_client.put(
        f"/api/templates/{tid}",
        json={"name": "TPL API 2", "html_template": "<html></html>"},
    )
    assert ur.status_code == 200

    dr = await async_api_client.delete(f"/api/templates/{tid}")
    assert dr.status_code == 200

    nf = await async_api_client.get(f"/api/templates/{tid}")
    assert nf.status_code == 404


@pytest.mark.asyncio
async def test_create_template_validation_error(async_api_client):
    r = await async_api_client.post("/api/templates/", json={"name": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_template_404(async_api_client):
    r = await async_api_client.get(f"/api/templates/{uuid4()}")
    assert r.status_code == 404
