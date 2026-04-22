from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from tests.factories import BlueprintFactory, ProjectFactory, SiteFactory, TaskFactory


@pytest.mark.asyncio
async def test_tasks_create_happy(async_api_client):
    site = SiteFactory(name="crud-task-site", domain="crud-task-site.example.com")
    resp = await async_api_client.post(
        "/api/tasks/",
        json={
            "main_keyword": "crud task keyword",
            "country": "DE",
            "language": "De",
            "target_site": str(site.id),
            "page_type": "article",
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("id")


@pytest.mark.asyncio
async def test_tasks_get_by_id_404(async_api_client):
    resp = await async_api_client.get(f"/api/tasks/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tasks_create_422(async_api_client):
    resp = await async_api_client.post("/api/tasks/", json={"main_keyword": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tasks_update_delete_cycle(async_api_client):
    task = TaskFactory(
        step_results={
            "primary_generation": {
                "status": "completed",
                "result": "<p>before</p>",
                "timestamp": datetime.utcnow().isoformat(),
            }
        }
    )
    task_id = str(task.id)

    update_resp = await async_api_client.put(
        f"/api/tasks/{task_id}/step-result",
        json={"step_name": "primary_generation", "result": "<p>after</p>"},
    )
    assert update_resp.status_code == 200

    get_resp = await async_api_client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert (
        get_resp.json().get("step_results", {}).get("primary_generation", {}).get("result") == "<p>after</p>"
    )

    delete_resp = await async_api_client.delete(f"/api/tasks/{task_id}")
    assert delete_resp.status_code == 200

    get_deleted = await async_api_client.get(f"/api/tasks/{task_id}")
    assert get_deleted.status_code == 404


@pytest.mark.asyncio
async def test_projects_create_happy(async_api_client):
    bp = BlueprintFactory()
    site = SiteFactory()
    resp = await async_api_client.post(
        "/api/projects/",
        json={
            "name": "crud-project",
            "blueprint_id": str(bp.id),
            "seed_keyword": "crud-seed",
            "country": "DE",
            "language": "De",
            "target_site": str(site.id),
            "use_site_template": False,
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("id")


@pytest.mark.asyncio
async def test_projects_get_by_id_404(async_api_client):
    resp = await async_api_client.get(f"/api/projects/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_projects_create_422(async_api_client):
    resp = await async_api_client.post("/api/projects/", json={"name": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_projects_update_delete_cycle(async_api_client):
    project = ProjectFactory(status="pending")
    project_id = str(project.id)

    update_resp = await async_api_client.post(f"/api/projects/{project_id}/archive")
    assert update_resp.status_code == 200
    assert update_resp.json().get("is_archived") is True

    get_resp = await async_api_client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json().get("is_archived") is True

    delete_resp = await async_api_client.delete(f"/api/projects/{project_id}", params={"force": "true"})
    assert delete_resp.status_code == 200

    get_deleted = await async_api_client.get(f"/api/projects/{project_id}")
    assert get_deleted.status_code == 404


@pytest.mark.asyncio
async def test_templates_create_happy(async_api_client):
    resp = await async_api_client.post(
        "/api/templates/",
        json={
            "name": "crud-template",
            "html_template": "<html><body>{{content}}</body></html>",
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("id")


@pytest.mark.asyncio
async def test_templates_get_by_id_404(async_api_client):
    resp = await async_api_client.get(f"/api/templates/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_templates_create_422(async_api_client):
    resp = await async_api_client.post("/api/templates/", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_templates_update_delete_cycle(async_api_client):
    create_resp = await async_api_client.post(
        "/api/templates/",
        json={
            "name": "crud-template-cycle",
            "html_template": "<html><body>{{content}}</body></html>",
            "is_active": True,
        },
    )
    template_id = create_resp.json()["id"]

    update_resp = await async_api_client.put(
        f"/api/templates/{template_id}",
        json={"name": "crud-template-cycle-updated"},
    )
    assert update_resp.status_code == 200

    get_resp = await async_api_client.get(f"/api/templates/{template_id}")
    assert get_resp.status_code == 200
    assert get_resp.json().get("name") == "crud-template-cycle-updated"

    delete_resp = await async_api_client.delete(f"/api/templates/{template_id}")
    assert delete_resp.status_code == 200

    get_deleted = await async_api_client.get(f"/api/templates/{template_id}")
    assert get_deleted.status_code == 404
