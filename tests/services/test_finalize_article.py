import pytest

from app.models.article import GeneratedArticle
from app.services.pipeline.assembly import finalize_article
from app.services.pipeline.context import PipelineContext
from app.services.pipeline_constants import STEP_CONTENT_FACT_CHECK, STEP_HTML_STRUCT, STEP_META_GEN
from tests.factories import ArticleFactory, ProjectFactory, SiteFactory, TaskFactory


def _bind_factories(db_session):
    SiteFactory._meta.sqlalchemy_session = db_session
    ProjectFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session
    ArticleFactory._meta.sqlalchemy_session = db_session


def _build_ctx(db_session, *, step_results, main_keyword="kw-test", with_project=False):
    _bind_factories(db_session)
    site = SiteFactory()
    project = ProjectFactory(site=site) if with_project else None
    task = TaskFactory(
        site=site,
        main_keyword=main_keyword,
        step_results=step_results,
        status="processing",
        project_id=project.id if project else None,
        log_events=[],
    )
    db_session.flush()
    return task, PipelineContext(db_session, str(task.id), auto_mode=True)


@pytest.mark.integration
def test_finalize_article_happy_path(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )

    class _FakeDedup:
        def __init__(self, db):
            self.db = db

        def extract_anchors(self, article_html, task_id, keyword):
            return [{"anchor": "x", "url": "/x"}]

        def save_anchors(self, project_id, task_id, anchors):
            return None

    monkeypatch.setattr("app.services.pipeline.assembly.ContentDeduplicator", _FakeDedup)
    step_results = {
        STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
        STEP_META_GEN: {"status": "completed", "result": '{"title":"T","description":"D"}'},
    }
    task, ctx = _build_ctx(db_session, step_results=step_results, with_project=True)

    article = finalize_article(ctx)
    db_session.refresh(task)
    assert article.title == "T"
    assert article.description == "D"
    assert (article.word_count or 0) > 0
    assert article.html_content
    assert task.status == "completed"
    saved = db_session.query(GeneratedArticle).filter(GeneratedArticle.task_id == task.id).all()
    assert len(saved) == 1


@pytest.mark.integration
def test_finalize_article_returns_article(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    step_results = {
        STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
        STEP_META_GEN: {"status": "completed", "result": '{"title":"T","description":"D"}'},
    }
    task, ctx = _build_ctx(db_session, step_results=step_results)
    result = finalize_article(ctx)
    assert isinstance(result, GeneratedArticle)
    assert result.task_id == task.id


@pytest.mark.integration
def test_finalize_article_raises_on_empty_html(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    rollback_calls = {"count": 0}
    real_rollback = db_session.rollback

    def _track_rollback():
        rollback_calls["count"] += 1
        return real_rollback()

    monkeypatch.setattr(db_session, "rollback", _track_rollback)
    task, ctx = _build_ctx(db_session, step_results={STEP_META_GEN: {"status": "completed", "result": "{}"}})

    with pytest.raises(ValueError, match="No HTML body"):
        finalize_article(ctx)
    assert task.status != "failed"
    assert rollback_calls["count"] == 0


@pytest.mark.integration
def test_finalize_article_title_fallback_on_empty_meta(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    task, ctx = _build_ctx(
        db_session,
        step_results={
            STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
            STEP_META_GEN: {"status": "completed", "result": "{}"},
        },
        main_keyword="cats and dogs",
    )
    article = finalize_article(ctx)
    assert article.title == "Cats And Dogs"
    assert article.task_id == task.id


@pytest.mark.integration
def test_finalize_article_upsert_updates_existing(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    step_results = {
        STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
        STEP_META_GEN: {"status": "completed", "result": '{"title":"new","description":"D"}'},
    }
    task, ctx = _build_ctx(db_session, step_results=step_results)
    existing = ArticleFactory(task_id=task.id, title="old", description="old", html_content="<p>old</p>")
    db_session.flush()
    finalize_article(ctx)
    db_session.flush()

    rows = db_session.query(GeneratedArticle).filter(GeneratedArticle.task_id == task.id).all()
    assert len(rows) == 1
    assert rows[0].id == existing.id
    assert rows[0].title == "new"


@pytest.mark.integration
def test_finalize_article_fact_check_strict_raises(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    monkeypatch.setattr("app.services.pipeline.assembly.settings.FACT_CHECK_ENABLED", True, raising=False)
    monkeypatch.setattr("app.services.pipeline.assembly.settings.FACT_CHECK_MODE", "strict", raising=False)
    monkeypatch.setattr("app.services.pipeline.assembly.settings.FACT_CHECK_FAIL_THRESHOLD", 1, raising=False)
    step_results = {
        STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
        STEP_META_GEN: {"status": "completed", "result": '{"title":"T","description":"D"}'},
        STEP_CONTENT_FACT_CHECK: {
            "status": "completed",
            "result": '{"verification_status":"fail","issues":[{"severity":"critical"}]}',
        },
    }
    _, ctx = _build_ctx(db_session, step_results=step_results)
    with pytest.raises(Exception, match="strict mode"):
        finalize_article(ctx)


@pytest.mark.integration
def test_finalize_article_does_not_call_notifiers(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    success_calls = {"count": 0}
    fail_calls = {"count": 0}
    monkeypatch.setattr(
        "app.services.pipeline.runner.notify_task_success",
        lambda *args, **kwargs: success_calls.__setitem__("count", success_calls["count"] + 1),
    )
    monkeypatch.setattr(
        "app.services.pipeline.runner.notify_task_failed",
        lambda *args, **kwargs: fail_calls.__setitem__("count", fail_calls["count"] + 1),
    )
    task, ctx = _build_ctx(
        db_session,
        step_results={
            STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
            STEP_META_GEN: {"status": "completed", "result": '{"title":"T","description":"D"}'},
        },
    )
    result = finalize_article(ctx)
    assert result.task_id == task.id
    assert success_calls["count"] == 0
    assert fail_calls["count"] == 0


@pytest.mark.integration
def test_finalize_article_does_not_touch_error_state(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    task, ctx = _build_ctx(
        db_session,
        step_results={
            STEP_HTML_STRUCT: {"status": "completed", "result": "<h1>T</h1><p>x</p>"},
            STEP_META_GEN: {"status": "completed", "result": '{"title":"T","description":"D"}'},
        },
    )
    assert task.error_log is None
    finalize_article(ctx)
    db_session.refresh(task)
    assert task.error_log is None

    task2, ctx2 = _build_ctx(db_session, step_results={STEP_META_GEN: {"status": "completed", "result": "{}"}})
    with pytest.raises(ValueError):
        finalize_article(ctx2)
    db_session.refresh(task2)
    assert task2.status != "failed"
