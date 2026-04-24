from __future__ import annotations

import pytest

from app.services.pipeline.context import PipelineContext
from app.services.site_utils import MARKUP_ONLY_SITE_KEY


@pytest.mark.integration
def test_pipeline_context_uses_seed_brand_for_markup_only_site(db_session, monkeypatch) -> None:
    monkeypatch.setattr(db_session, "commit", db_session.flush)

    from tests.factories import BlueprintFactory, ProjectFactory, SiteFactory, TaskFactory

    BlueprintFactory._meta.sqlalchemy_session = db_session
    SiteFactory._meta.sqlalchemy_session = db_session
    ProjectFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    placeholder_site = SiteFactory(name=MARKUP_ONLY_SITE_KEY, domain=MARKUP_ONLY_SITE_KEY)
    blueprint = BlueprintFactory()
    project = ProjectFactory(
        blueprint=blueprint,
        site=placeholder_site,
        seed_keyword="golden tiger",
    )
    task = TaskFactory(
        site=placeholder_site,
        project_id=project.id,
        main_keyword="fallback keyword",
    )
    db_session.flush()

    ctx = PipelineContext(db_session, str(task.id), auto_mode=True)

    assert ctx.is_markup_only is True
    assert ctx.site_name == "Golden Tiger"
