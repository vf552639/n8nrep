import pytest

from app.services.pipeline.context import PipelineContext
from app.services.pipeline.errors import LLMError, ParseError, ValidationError
from app.services.pipeline.runner import _run_phase, run_pipeline
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline_constants import STEP_SCRAPING


@pytest.mark.integration
def test_run_phase_retries_llm_error_until_success(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    from tests.factories import SiteFactory, TaskFactory

    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    task = TaskFactory(site=site, step_results={}, status="pending")
    db_session.flush()

    attempts = {"count": 0}

    class FlakyDraftStep:
        name = "draft_retry_test"
        policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

        def run(self, ctx):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise LLMError("temporary llm outage")
            return StepResult(status="completed", result="<p>ok</p>")

    ctx = PipelineContext(db_session, str(task.id), auto_mode=True)
    _run_phase(ctx, FlakyDraftStep())
    db_session.refresh(task)

    assert attempts["count"] == 3
    assert task.step_results["draft_retry_test"]["status"] == "completed"


@pytest.mark.integration
def test_skip_on_parse_error_marks_skipped_and_allows_next_step(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    from tests.factories import SiteFactory, TaskFactory

    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    task = TaskFactory(site=site, step_results={}, status="pending")
    db_session.flush()

    class StructureFactCheckStep:
        name = "structure_fact_checking"
        policy = StepPolicy(skip_on=(LLMError, ParseError))

        def run(self, ctx):
            raise ParseError("invalid json from fact check")

    class NextStep:
        name = "next_after_skip"
        policy = StepPolicy()

        def run(self, ctx):
            return StepResult(status="completed", result="after-skip")

    ctx = PipelineContext(db_session, str(task.id), auto_mode=True)
    _run_phase(ctx, StructureFactCheckStep())
    _run_phase(ctx, NextStep())
    db_session.refresh(task)

    assert task.step_results["structure_fact_checking"]["status"] == "skipped"
    assert task.step_results["next_after_skip"]["status"] == "completed"


@pytest.mark.integration
def test_validation_error_in_finalize_article_sets_task_failed(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr("app.services.pipeline.runner.notify_task_success", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.runner.notify_task_failed", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.runner._resolve_steps", lambda ctx: [])
    monkeypatch.setattr(
        "app.services.pipeline.runner.finalize_article",
        lambda ctx: (_ for _ in ()).throw(ValidationError("bad final html")),
    )
    from tests.factories import SiteFactory, TaskFactory

    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    task = TaskFactory(site=site, step_results={}, status="pending")
    db_session.flush()

    run_pipeline(db_session, str(task.id), auto_mode=True)
    db_session.refresh(task)

    assert task.status == "failed"
    assert task.error_log


@pytest.mark.integration
def test_serp_step_paused_when_not_auto_mode(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr("app.services.pipeline.runner.notify_task_success", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.runner.notify_task_failed", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.services.pipeline.steps.serp_step.fetch_serp_data",
        lambda *a, **k: {"urls": ["https://x.example/"], "source": "mock"},
    )
    from tests.factories import SiteFactory, TaskFactory

    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    task = TaskFactory(site=site, step_results={}, status="pending")
    db_session.flush()

    run_pipeline(db_session, str(task.id))  # auto_mode=False by default
    db_session.refresh(task)

    step_results = task.step_results or {}
    pause = step_results.get("_pipeline_pause") or {}

    assert task.status == "paused"
    assert pause.get("active") is True
    assert pause.get("reason") == "serp_review"
    assert STEP_SCRAPING not in step_results
