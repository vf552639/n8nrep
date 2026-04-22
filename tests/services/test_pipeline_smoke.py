"""Smoke checks for pipeline helpers (uses integration DB when configured)."""

import json

import pytest

from app.schemas.jsonb_adapter import read_step_results
from app.services.pipeline import PipelineContext, add_log, phase_serp, run_pipeline
from app.services.pipeline_constants import STEP_SERP


@pytest.mark.integration
def test_add_log_appends_and_truncates(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr("app.services.pipeline.settings", type("S", (), {"TEST_MODE": False})())
    from tests.factories import SiteFactory, TaskFactory

    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    db_session.flush()
    task = TaskFactory(target_site_id=site.id, log_events=[])
    db_session.flush()

    for i in range(3):
        add_log(db_session, task, f"msg-{i}", step="test")
    db_session.refresh(task)
    assert len(task.log_events) == 3
    assert task.log_events[-1]["msg"] == "msg-2"


@pytest.mark.integration
def test_phase_serp_merges_project_competitor_urls(db_session, monkeypatch):
    """User competitor URLs merge into SERP urls with domain dedup (task41)."""
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    from tests.factories import (
        BlueprintFactory,
        BlueprintPageFactory,
        ProjectFactory,
        SiteFactory,
        TaskFactory,
    )

    BlueprintFactory._meta.sqlalchemy_session = db_session
    BlueprintPageFactory._meta.sqlalchemy_session = db_session
    SiteFactory._meta.sqlalchemy_session = db_session
    ProjectFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    bp = BlueprintFactory()
    page = BlueprintPageFactory(blueprint=bp, page_slug="p1", keyword_template="{seed}")
    db_session.flush()
    project = ProjectFactory(
        blueprint=bp,
        site=site,
        competitor_urls=["https://user-only.example/page", "example.com"],
    )
    db_session.flush()
    task = TaskFactory(
        site=site,
        project_id=project.id,
        blueprint_page_id=page.id,
        main_keyword="kw",
        serp_data=None,
        step_results={},
    )
    db_session.flush()

    def _fake_fetch(keyword, country, language, serp_config=None):
        return {
            "source": "test",
            "urls": ["https://www.example.com/from-serp"],
            "organic_results": [],
        }

    monkeypatch.setattr("app.services.pipeline.fetch_serp_data", _fake_fetch)

    ctx = PipelineContext(db_session, str(task.id), auto_mode=True)
    phase_serp(ctx)
    db_session.refresh(task)

    sd = task.serp_data
    assert isinstance(sd, dict)
    urls = sd.get("urls") or []
    assert "https://www.example.com/from-serp" in urls
    assert "https://user-only.example/page" in urls
    assert sd.get("user_competitor_urls") == [
        "https://user-only.example/page",
        "https://example.com/",
    ]
    dups = sd.get("user_competitor_duplicates") or []
    assert "https://example.com/" in dups

    serp_step = (task.step_results or {}).get(STEP_SERP, {})
    summary = json.loads(serp_step.get("result") or "{}")
    assert summary.get("user_competitor_urls_count") == 2
    assert "https://example.com/" in (summary.get("user_competitor_duplicates") or [])


@pytest.mark.integration
def test_run_pipeline_minimal_happy_path(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr("app.services.pipeline.notify_task_success", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.notify_task_failed", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.settings.TEST_MODE", False, raising=False)
    monkeypatch.setattr("app.services.pipeline.settings.FACT_CHECK_ENABLED", False, raising=False)
    from tests.factories import (
        BlueprintFactory,
        BlueprintPageFactory,
        PromptFactory,
        SiteFactory,
        TaskFactory,
    )

    BlueprintFactory._meta.sqlalchemy_session = db_session
    BlueprintPageFactory._meta.sqlalchemy_session = db_session
    PromptFactory._meta.sqlalchemy_session = db_session
    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    bp = BlueprintFactory()
    page = BlueprintPageFactory(
        blueprint=bp,
        page_slug="minimal",
        keyword_template="{seed}",
        pipeline_preset="custom",
        pipeline_steps_custom=["primary_generation"],
    )
    PromptFactory(
        agent_name="primary_generation",
        system_prompt="You are a writer.",
        user_prompt="Write HTML article for {{keyword}}",
        model="openai/gpt-4o-mini",
    )
    db_session.flush()

    task = TaskFactory(
        site=site,
        blueprint_page_id=page.id,
        main_keyword="minimal smoke keyword",
        step_results={},
        log_events=[],
        status="pending",
    )
    db_session.flush()

    def _fake_generate_text(system_prompt, user_prompt, **kwargs):
        return ("<h1>Title</h1><p>Body</p>", 0.0, kwargs.get("model", "fake-model"), {"usage": {}})

    monkeypatch.setattr("app.services.pipeline.generate_text", _fake_generate_text)

    run_pipeline(db_session, str(task.id))
    db_session.refresh(task)

    assert task.status == "completed"
    assert len(task.log_events or []) > 0
    step_results = read_step_results(task.step_results)
    assert "primary_generation" in step_results
