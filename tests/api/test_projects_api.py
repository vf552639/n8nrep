from __future__ import annotations

from uuid import uuid4

import pytest

from tests.factories import BlueprintFactory, BlueprintPageFactory, ProjectFactory, SiteFactory


@pytest.mark.asyncio
async def test_list_projects(async_api_client):
    r = await async_api_client.get("/api/projects/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_preview_project(async_api_client):
    bp = BlueprintFactory()
    site = SiteFactory()
    BlueprintPageFactory(blueprint=bp, page_slug="p1", keyword_template="{seed}")
    r = await async_api_client.post(
        "/api/projects/preview",
        json={
            "blueprint_id": str(bp.id),
            "seed_keyword": "seedkw",
            "country": "DE",
            "language": "De",
            "target_site": str(site.id),
            "use_site_template": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "pages" in body and "warnings" in body


@pytest.mark.asyncio
async def test_cluster_keywords(async_api_client):
    bp = BlueprintFactory()
    BlueprintPageFactory(
        blueprint=bp,
        page_slug="pg1",
        page_title="T",
        keyword_template="{seed}",
    )
    r = await async_api_client.post(
        "/api/projects/cluster-keywords",
        json={"blueprint_id": str(bp.id), "keywords": ["one", "two"]},
    )
    assert r.status_code == 200
    assert "clustered" in r.json()


@pytest.mark.asyncio
async def test_create_project_happy(async_api_client):
    bp = BlueprintFactory()
    site = SiteFactory()
    r = await async_api_client.post(
        "/api/projects/",
        json={
            "name": "New Proj API",
            "blueprint_id": str(bp.id),
            "seed_keyword": "unique_seed_1",
            "country": "DE",
            "language": "De",
            "target_site": str(site.id),
            "use_site_template": True,
        },
    )
    assert r.status_code == 200
    assert "id" in r.json()


@pytest.mark.asyncio
async def test_create_project_with_competitor_urls(async_api_client):
    bp = BlueprintFactory()
    site = SiteFactory()
    r = await async_api_client.post(
        "/api/projects/",
        json={
            "name": "Proj With Competitors",
            "blueprint_id": str(bp.id),
            "seed_keyword": "unique_seed_comp_urls_1",
            "country": "DE",
            "language": "De",
            "target_site": str(site.id),
            "use_site_template": True,
            "competitor_urls": ["  example.com/foo  ", "https://other.test/path"],
        },
    )
    assert r.status_code == 200
    pid = r.json()["id"]
    gr = await async_api_client.get(f"/api/projects/{pid}")
    assert gr.status_code == 200
    urls = gr.json().get("competitor_urls") or []
    assert "https://example.com/foo" in urls
    assert "https://other.test/path" in urls


@pytest.mark.asyncio
async def test_create_project_validation_error(async_api_client):
    r = await async_api_client.post("/api/projects/", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_project_404(async_api_client):
    r = await async_api_client.get(f"/api/projects/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_archive_project(async_api_client):
    p = ProjectFactory(status="completed", is_archived=False)
    pid = str(p.id)
    r = await async_api_client.post(f"/api/projects/{pid}/archive")
    assert r.status_code == 200
    assert r.json().get("is_archived") is True


@pytest.mark.asyncio
async def test_delete_project_without_force(async_api_client):
    p = ProjectFactory(status="failed")
    pid = str(p.id)
    r = await async_api_client.delete(f"/api/projects/{pid}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_project_with_force(async_api_client):
    p = ProjectFactory(status="pending")
    pid = str(p.id)
    r = await async_api_client.delete(f"/api/projects/{pid}", params={"force": "true"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_selected_projects(async_api_client):
    p1 = ProjectFactory(status="failed")
    p2 = ProjectFactory(status="failed")
    r = await async_api_client.post(
        "/api/projects/delete-selected",
        json={"project_ids": [str(p1.id), str(p2.id)], "force": False},
    )
    assert r.status_code == 200
    assert r.json().get("deleted") == 2


@pytest.mark.asyncio
async def test_clone_and_start(async_api_client):
    bp = BlueprintFactory()
    site = SiteFactory()
    src = ProjectFactory(
        blueprint=bp,
        site=site,
        status="failed",
        seed_keyword="clone_seed_x",
    )
    pid = str(src.id)
    cr = await async_api_client.post(
        f"/api/projects/{pid}/clone",
        json={"name": "Cloned Proj", "seed_keyword": "clone_seed_y"},
    )
    assert cr.status_code == 200
    new_id = cr.json().get("id")
    assert new_id

    sr = await async_api_client.post(f"/api/projects/{new_id}/start")
    assert sr.status_code == 200
    assert "celery_task_id" in sr.json()


@pytest.mark.asyncio
async def test_reset_status(async_api_client):
    p = ProjectFactory(status="pending")
    pid = str(p.id)
    r = await async_api_client.post(f"/api/projects/{pid}/reset-status")
    assert r.status_code == 200
    assert r.json().get("status") == "failed"
