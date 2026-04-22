"""End-to-end smoke check for full pipeline preset (task43)."""

import pytest

from app.models.article import GeneratedArticle
from app.services.pipeline import run_pipeline
from app.services.pipeline_presets import PIPELINE_PRESETS
from tests.factories import (
    BlueprintFactory,
    BlueprintPageFactory,
    PromptFactory,
    SiteFactory,
    TaskFactory,
)

LLM_AGENTS = [
    "ai_structure_analysis",
    "chunk_cluster_analysis",
    "competitor_structure_analysis",
    "final_structure_analysis",
    "structure_fact_checking",
    "primary_generation",
    "competitor_comparison",
    "reader_opinion",
    "improver",
    "final_editing",
    "html_structure",
    "meta_generation",
]

_HTML = "<h1>Smoke</h1><p>Mock content paragraph.</p>"
_META = '{"title":"Smoke Title","description":"Smoke desc","h1":"Smoke H1"}'
_JSON = '{"sections":[{"title":"S1","subsections":[]}]}'


@pytest.mark.integration
def test_run_pipeline_full_preset_smoke(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)

    BlueprintFactory._meta.sqlalchemy_session = db_session
    BlueprintPageFactory._meta.sqlalchemy_session = db_session
    PromptFactory._meta.sqlalchemy_session = db_session
    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    blueprint = BlueprintFactory()
    page = BlueprintPageFactory(
        blueprint=blueprint,
        page_slug="smoke-full",
        keyword_template="{seed}",
        pipeline_preset="full",
        pipeline_steps_custom=None,
    )
    for name in LLM_AGENTS:
        PromptFactory(
            agent_name=name,
            system_prompt="You are an assistant.",
            user_prompt="Respond for {{keyword}}",
            model="openai/gpt-4o-mini",
        )

    task = TaskFactory(
        site=site,
        blueprint_page_id=page.id,
        main_keyword="smoke test keyword",
        country="DE",
        language="De",
        step_results={},
        log_events=[],
        status="pending",
    )
    db_session.flush()

    def _fake_call_agent(ctx, agent_name, context, response_format=None, variables=None):
        if agent_name == "meta_generation":
            return (_META, 0.0, "fake-model", {}, {})
        if any(x in agent_name for x in ("structure", "analysis", "fact_check")):
            return (_JSON, 0.0, "fake-model", {}, {})
        return (_HTML, 0.0, "fake-model", {}, {})

    def _fake_call_agent_excl(ctx, agent_name, context, step_constant=None, **kwargs):
        return (_HTML, 0.0, "fake-model", {}, {}, {})

    # Steps import call helpers directly, so patch step-module bindings.
    monkeypatch.setattr("app.services.pipeline.steps.outline_step.call_agent", _fake_call_agent)
    monkeypatch.setattr("app.services.pipeline.steps.meta_step.call_agent", _fake_call_agent)
    monkeypatch.setattr("app.services.pipeline.steps.html_assembly_step.call_agent", _fake_call_agent)
    monkeypatch.setattr("app.services.pipeline.steps.image_prompts_step.call_agent", _fake_call_agent)
    monkeypatch.setattr("app.services.pipeline.steps.draft_step.call_agent", _fake_call_agent)
    monkeypatch.setattr("app.services.pipeline.steps.legal_step.call_agent_with_exclude_validation", _fake_call_agent_excl)
    monkeypatch.setattr("app.services.pipeline.steps.final_editing_step.call_agent_with_exclude_validation", _fake_call_agent_excl)
    monkeypatch.setattr("app.services.pipeline.steps.draft_step.call_agent_with_exclude_validation", _fake_call_agent_excl)
    monkeypatch.setattr(
        "app.services.pipeline.steps.serp_step.fetch_serp_data",
        lambda keyword, country, language, serp_config=None, force_refresh=False: {
            "source": "smoke",
            "urls": ["https://example.com/page1"],
            "organic_results": [{"url": "https://example.com/page1", "title": "T"}],
            "paa": [],
            "featured_snippet": None,
        },
    )
    monkeypatch.setattr(
        "app.services.pipeline.steps.serp_step.scrape_urls",
        lambda urls, max_urls=10, timeout=15: {
            "merged_text": "Mock competitor text.",
            "average_word_count": 1200,
            "headers_structure": [],
            "total_attempted": len(urls or []),
            "successful_scrapes": len(urls or []),
            "raw_results": [
                {"domain": "example.com", "url": u, "title": "Mock"} for u in (urls or [])
            ],
            "scraped_titles": ["Mock"],
            "scraped_descriptions": ["Mock"],
            "failed_results": [],
            "serper_count": 0,
            "direct_count": len(urls or []),
            "cache_hits": 0,
            "cache_misses": len(urls or []),
        },
    )
    monkeypatch.setattr(
        "app.services.pipeline.assembly.generate_full_page",
        lambda db, site_id, html_content, title, description, project_id=None: (
            f"<html><body>{html_content}</body></html>"
        ),
    )
    monkeypatch.setattr("app.services.pipeline.runner.notify_task_success", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.runner.notify_task_failed", lambda *a, **k: None)
    monkeypatch.setattr("app.services.pipeline.runner.settings.TEST_MODE", False, raising=False)
    monkeypatch.setattr("app.services.pipeline.steps.html_assembly_step.settings.FACT_CHECK_ENABLED", False, raising=False)

    run_pipeline(db_session, str(task.id), auto_mode=True)
    db_session.refresh(task)

    full_steps = PIPELINE_PRESETS["full"]

    assert task.status == "completed", f"status={task.status}, logs={(task.log_events or [])[-3:]}"

    step_results = task.step_results or {}
    for step in full_steps:
        assert step in step_results, f"step '{step}' missing from step_results"
        assert step_results[step].get("status") in {
            "completed",
            "completed_with_warnings",
            "skipped",
        }, f"step '{step}' has status={step_results[step].get('status')}"

    article = db_session.query(GeneratedArticle).filter_by(task_id=task.id).first()
    assert article is not None, "GeneratedArticle not created"
    assert article.html_content, "html_content is empty"
    assert article.title, "title is empty"
    assert article.description is not None
    assert len(task.log_events or []) > 0
