from __future__ import annotations

import io
from uuid import uuid4

import pytest

from tests.factories import SiteFactory, TaskFactory


@pytest.mark.asyncio
async def test_list_tasks_with_filters(async_api_client):
    site = SiteFactory()
    TaskFactory(site=site, main_keyword="unique_search_kw_abc")
    r = await async_api_client.get(
        "/api/tasks/",
        params={"status": "pending", "site_id": str(site.id), "search": "unique_search"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body


@pytest.mark.asyncio
async def test_create_task_happy(async_api_client):
    site = SiteFactory(name="task_create_site", domain="task-create.example.com")
    r = await async_api_client.post(
        "/api/tasks/",
        json={
            "main_keyword": "test keyword",
            "country": "DE",
            "language": "De",
            "target_site": str(site.id),
            "page_type": "article",
        },
    )
    assert r.status_code == 200
    assert "id" in r.json()


@pytest.mark.asyncio
async def test_create_task_validation_error(async_api_client):
    r = await async_api_client.post("/api/tasks/", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_bulk_create_tasks(async_api_client):
    SiteFactory(name="bulk_site", domain="bulk.example.com")
    csv_body = "keyword,country,language,site_name\nkw1,DE,De,bulk_site\n"
    r = await async_api_client.post(
        "/api/tasks/bulk",
        files={"file": ("tasks.csv", io.BytesIO(csv_body.encode()), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json().get("tasks_created", 0) >= 1


@pytest.mark.asyncio
async def test_get_task_404(async_api_client):
    r = await async_api_client.get(f"/api/tasks/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_then_404(async_api_client):
    t = TaskFactory()
    tid = str(t.id)
    d1 = await async_api_client.delete(f"/api/tasks/{tid}")
    assert d1.status_code == 200
    d2 = await async_api_client.delete(f"/api/tasks/{tid}")
    assert d2.status_code == 404


@pytest.mark.asyncio
async def test_delete_selected_tasks(async_api_client):
    t = TaskFactory()
    tid = str(t.id)
    r = await async_api_client.post("/api/tasks/delete-selected", json={"task_ids": [tid]})
    assert r.status_code == 200
    assert r.json().get("deleted") == 1


@pytest.mark.asyncio
async def test_retry_failed_task(async_api_client):
    t = TaskFactory(status="failed")
    tid = str(t.id)
    r = await async_api_client.post(f"/api/tasks/{tid}/retry")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_approve_requires_waiting(async_api_client):
    t = TaskFactory(status="pending")
    tid = str(t.id)
    r = await async_api_client.post(f"/api/tasks/{tid}/approve")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_serp_data_serp_urls_images(async_api_client):
    t = TaskFactory(
        serp_data={
            "organic_results": [],
            "urls": ["https://example.com/a"],
            "source": "test",
        },
    )
    tid = str(t.id)
    r1 = await async_api_client.get(f"/api/tasks/{tid}/serp-data")
    assert r1.status_code == 200
    r2 = await async_api_client.get(f"/api/tasks/{tid}/serp-urls")
    assert r2.status_code == 200
    r3 = await async_api_client.get(f"/api/tasks/{tid}/images")
    assert r3.status_code == 200
    assert r3.json().get("images") == []
