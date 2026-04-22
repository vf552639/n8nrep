from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_authors_list(async_api_client):
    r = await async_api_client.get("/api/authors/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_author_crud(async_api_client):
    payload = {
        "author": "API Author",
        "country": "DE",
        "country_full": None,
        "language": "De",
        "bio": None,
        "co_short": None,
        "city": None,
        "imitation": None,
        "year": None,
        "face": None,
        "target_audience": None,
        "rhythms_style": None,
        "exclude_words": None,
    }
    r = await async_api_client.post("/api/authors/", json=payload)
    assert r.status_code == 200
    aid = r.json()["id"]

    gr = await async_api_client.get("/api/authors/")
    assert gr.status_code == 200
    assert any(x["id"] == aid for x in gr.json())

    ur = await async_api_client.put(f"/api/authors/{aid}", json={**payload, "author": "Renamed"})
    assert ur.status_code == 200

    dr = await async_api_client.delete(f"/api/authors/{aid}")
    assert dr.status_code == 200


@pytest.mark.asyncio
async def test_create_author_validation_error(async_api_client):
    r = await async_api_client.post("/api/authors/", json={"author": "x"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_author_404(async_api_client):
    r = await async_api_client.put(
        "/api/authors/999999999",
        json={
            "author": "N",
            "country": "DE",
            "language": "De",
        },
    )
    assert r.status_code == 404
