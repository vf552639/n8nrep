from __future__ import annotations

from uuid import uuid4

import pytest

from tests.factories import ArticleFactory


@pytest.mark.asyncio
async def test_articles_list(async_api_client):
    r = await async_api_client.get("/api/articles/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_article_404(async_api_client):
    r = await async_api_client.get(f"/api/articles/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_article(async_api_client):
    art = ArticleFactory()
    aid = str(art.id)
    r = await async_api_client.patch(
        f"/api/articles/{aid}",
        json={"html_content": "<p>patched</p>", "title": "T2"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "T2"
