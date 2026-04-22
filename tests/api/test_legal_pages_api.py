from __future__ import annotations

from uuid import uuid4

import pytest

from tests.factories import BlueprintFactory, BlueprintPageFactory


@pytest.mark.asyncio
async def test_legal_meta_page_types(async_api_client):
    r = await async_api_client.get("/api/legal-pages/meta/page-types")
    assert r.status_code == 200
    assert "page_types" in r.json()


@pytest.mark.asyncio
async def test_legal_for_blueprint(async_api_client):
    bp = BlueprintFactory()
    BlueprintPageFactory(blueprint=bp, page_type="privacy_policy")
    r = await async_api_client.get(f"/api/legal-pages/for-blueprint/{bp.id}")
    assert r.status_code == 200
    assert "legal_page_types" in r.json()


@pytest.mark.asyncio
async def test_legal_by_page_type(async_api_client):
    r = await async_api_client.get("/api/legal-pages/by-page-type/privacy_policy")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_legal_crud(async_api_client):
    r = await async_api_client.post(
        "/api/legal-pages/",
        json={
            "name": "LP API Test",
            "page_type": "privacy_policy",
            "content": "Content body for legal page test.",
            "content_format": "text",
            "is_active": True,
        },
    )
    assert r.status_code == 200
    lid = r.json()["id"]

    gr = await async_api_client.get(f"/api/legal-pages/{lid}")
    assert gr.status_code == 200

    pr = await async_api_client.put(
        f"/api/legal-pages/{lid}",
        json={"name": "LP API Test 2"},
    )
    assert pr.status_code == 200

    dr = await async_api_client.delete(f"/api/legal-pages/{lid}")
    assert dr.status_code == 200

    nf = await async_api_client.get(f"/api/legal-pages/{lid}")
    assert nf.status_code == 404


@pytest.mark.asyncio
async def test_get_legal_404(async_api_client):
    r = await async_api_client.get(f"/api/legal-pages/{uuid4()}")
    assert r.status_code == 404
