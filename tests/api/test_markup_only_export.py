from __future__ import annotations

import io
import uuid
import zipfile

import pytest

from app.models.project import SiteProject
from tests.factories import ArticleFactory, BlueprintFactory, BlueprintPageFactory, TaskFactory


@pytest.mark.asyncio
async def test_markup_only_project_docx_uses_seed_brand(async_api_client, api_db_session) -> None:
    blueprint = BlueprintFactory()
    page = BlueprintPageFactory(
        blueprint=blueprint,
        page_slug="home",
        page_title="Home",
        keyword_template="{seed}",
        sort_order=1,
    )

    create_resp = await async_api_client.post(
        "/api/projects/",
        json={
            "name": "Markup only project",
            "blueprint_id": str(blueprint.id),
            "seed_keyword": "golden tiger",
            "country": "DE",
            "language": "De",
            "target_site": "",
            "use_site_template": False,
        },
    )
    assert create_resp.status_code == 200
    project_id = create_resp.json()["id"]

    project_uuid = uuid.UUID(project_id)
    project = api_db_session.query(SiteProject).filter(SiteProject.id == project_uuid).first()
    assert project is not None

    task = TaskFactory(
        project_id=project.id,
        blueprint_page_id=page.id,
        target_site_id=project.site_id,
        main_keyword="golden tiger",
        status="completed",
        step_results={},
    )
    ArticleFactory(
        task=task,
        title="Golden Tiger Review",
        html_content="<h1>Golden Tiger</h1><p>Body</p>",
    )
    api_db_session.flush()

    export_resp = await async_api_client.get(f"/api/projects/{project_id}/export-docx")
    assert export_resp.status_code == 200
    docx_bytes = export_resp.content
    assert docx_bytes

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")

    assert "__markup_only__" not in xml
    assert "Golden Tiger" in xml
