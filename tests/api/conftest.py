"""Autouse mocks + Celery eager for HTTP API tests (task37 §1.4)."""

from __future__ import annotations

from typing import Any

import pytest


def _fake_generate_text(
    system_prompt: str,
    user_prompt: str,
    **kwargs: Any,
) -> tuple[str, float, str, dict[str, Any] | None]:
    return (
        '{"assignments": {}, "unassigned": []}',
        0.0,
        kwargs.get("model", "test-model"),
        {"prompt_tokens": 0, "completion_tokens": 0},
    )


@pytest.fixture(scope="session", autouse=True)
def _celery_eager():
    from app.workers.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield


@pytest.fixture(autouse=True)
def _clear_structlog_context():
    import structlog

    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


class _FakeCeleryAsyncResult:
    id = "00000000-0000-0000-0000-000000000099"


def _fake_celery_submit(*_a: Any, **_kw: Any) -> _FakeCeleryAsyncResult:
    return _FakeCeleryAsyncResult()


@pytest.fixture(autouse=True)
def _mock_external_services(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.llm.generate_text", _fake_generate_text)
    monkeypatch.setattr("app.services.pipeline.generate_text", _fake_generate_text)
    monkeypatch.setattr("app.services.keyword_clusterer.generate_text", _fake_generate_text)
    monkeypatch.setattr("app.api.prompts.generate_text", _fake_generate_text)

    def _fetch_serp(
        keyword: str,
        country_code: str,
        language_code: str,
        serp_config=None,
        force_refresh: bool = False,
    ):
        return {
            "results": [],
            "keyword": keyword,
            "organic_results": [],
            "urls": [],
        }

    monkeypatch.setattr("app.services.serp.fetch_serp_data", _fetch_serp)
    monkeypatch.setattr("app.services.pipeline.fetch_serp_data", _fetch_serp)

    def _scrape(urls, max_urls=10, timeout=15):
        return {u: {"text": "", "title": ""} for u in urls}

    monkeypatch.setattr("app.services.scraper.scrape_urls", _scrape)
    monkeypatch.setattr("app.services.pipeline.scrape_urls", _scrape)

    def _fetch_meta(url, timeout=12):
        return {"title": "", "description": "", "url": url, "domain": ""}

    monkeypatch.setattr("app.services.scraper.fetch_url_meta", _fetch_meta)
    monkeypatch.setattr("app.api.tasks.fetch_url_meta", _fetch_meta)

    def _serp_health_ok(force_refresh: bool = False):
        return {
            "overall": "ok",
            "dataforseo": {"status": "ok"},
            "serpapi": {"status": "ok"},
        }

    monkeypatch.setattr("app.services.serp.get_serp_health", _serp_health_ok)

    from app.workers import tasks as worker_tasks

    for _name in (
        "process_generation_task",
        "process_site_project",
        "advance_project",
        "process_project_page",
    ):
        _t = getattr(worker_tasks, _name)
        monkeypatch.setattr(_t, "delay", _fake_celery_submit)
        monkeypatch.setattr(_t, "apply_async", _fake_celery_submit)

    import celery as celery_mod

    def _fake_chain(*_args: Any, **_kwargs: Any):
        class _C:
            def apply_async(self, *_a: Any, **_kw: Any) -> _FakeCeleryAsyncResult:
                return _FakeCeleryAsyncResult()

        return _C()

    monkeypatch.setattr(celery_mod, "chain", _fake_chain)


@pytest.fixture(autouse=True)
def _projects_worker_check_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """start_project pings Celery inspect — not available in API test process."""
    monkeypatch.setattr("app.api.projects._ensure_worker_available", lambda: None)


@pytest.fixture(autouse=True)
def _bind_factories_session(api_db_session) -> None:
    """factory_boy needs the same rolled-back session as httpx + get_db override."""
    import tests.factories as fac

    for cls in (
        fac.SiteFactory,
        fac.AuthorFactory,
        fac.BlueprintFactory,
        fac.BlueprintPageFactory,
        fac.ProjectFactory,
        fac.TemplateFactory,
        fac.LegalPageTemplateFactory,
        fac.PromptFactory,
        fac.TaskFactory,
        fac.ArticleFactory,
    ):
        cls._meta.sqlalchemy_session = api_db_session
    yield
