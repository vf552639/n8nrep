from __future__ import annotations

import pytest

from app.schemas.log_event import LogEvent
from app.workers.celery_app import celery_app
from app.workers.tasks import process_generation_task


@pytest.fixture(scope="module", autouse=True)
def celery_eager():
    prev_always_eager = celery_app.conf.task_always_eager
    prev_eager_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    try:
        yield
    finally:
        celery_app.conf.task_always_eager = prev_always_eager
        celery_app.conf.task_eager_propagates = prev_eager_propagates


@pytest.mark.integration
def test_process_generation_task_happy_path(db_session, monkeypatch):
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
        page_slug="worker-minimal",
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
        main_keyword="worker happy path keyword",
        status="pending",
        step_results={},
        log_events=[],
    )
    db_session.commit()

    def _fake_generate_text(system_prompt, user_prompt, **kwargs):
        return ("<h1>Title</h1><p>Body</p>", 0.0, kwargs.get("model", "fake-model"), {"usage": {}})

    monkeypatch.setattr("app.services.pipeline.generate_text", _fake_generate_text)
    process_generation_task.delay(str(task.id))

    db_session.refresh(task)
    assert task.status == "completed"
    events = task.log_events or []
    assert len(events) > 0
    for entry in events:
        LogEvent(**entry)


@pytest.mark.integration
def test_process_generation_task_llm_failure(db_session, monkeypatch):
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
        page_slug="worker-fail",
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
        main_keyword="worker failure keyword",
        status="pending",
        step_results={},
        log_events=[],
    )
    db_session.commit()

    def _raise_generate_text(system_prompt, user_prompt, **kwargs):
        raise RuntimeError("mock llm failure")

    monkeypatch.setattr("app.services.pipeline.generate_text", _raise_generate_text)
    process_generation_task.delay(str(task.id))

    db_session.refresh(task)
    assert task.status == "failed"
    assert task.error_log
