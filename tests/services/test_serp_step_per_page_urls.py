from __future__ import annotations

from unittest.mock import patch

from app.services.pipeline.steps.serp_step import SerpStep


class _FakeTask:
    def __init__(
        self,
        project_id,
        blueprint_page_id=None,
        serp_config=None,
        main_keyword="kw",
        country="US",
        language="en",
    ):
        self.id = "task-1"
        self.project_id = project_id
        self.blueprint_page_id = blueprint_page_id
        self.serp_config = serp_config or {}
        self.main_keyword = main_keyword
        self.country = country
        self.language = language
        self.serp_data = None
        self.step_results = {}
        self.status = "pending"


class _FakeBlueprintPage:
    def __init__(self, slug):
        self.id = "bp-page-1"
        self.page_slug = slug


class _FakeProject:
    def __init__(self, competitor_urls=None, project_keywords=None):
        self.id = "proj-1"
        self.competitor_urls = competitor_urls or []
        self.project_keywords = project_keywords or {}


class _FakeQuery:
    def __init__(self, obj):
        self.obj = obj

    def filter(self, *a, **kw):
        return self

    def first(self):
        return self.obj


class _FakeDB:
    def __init__(self, project, blueprint_page):
        self._project = project
        self._page = blueprint_page

    def query(self, model):
        from app.models.blueprint import BlueprintPage
        from app.models.project import SiteProject

        if model is SiteProject:
            return _FakeQuery(self._project)
        if model is BlueprintPage:
            return _FakeQuery(self._page)
        return _FakeQuery(None)

    def commit(self):
        pass

    def add(self, *a, **kw):
        pass


class _FakeCtx:
    def __init__(self, db, task, auto_mode=True):
        self.db = db
        self.task = task
        self.auto_mode = auto_mode


@patch("app.services.pipeline.steps.serp_step.add_log")
@patch("app.services.pipeline.steps.serp_step.fetch_serp_data")
def test_serp_step_engine_off_uses_only_per_page_urls(mock_fetch, mock_log) -> None:
    project = _FakeProject(
        competitor_urls=["https://global.example.com"],
        project_keywords={
            "clustered": {
                "home": {
                    "page_title": "Home",
                    "competitor_urls": ["https://homepage-rival.com/x"],
                }
            }
        },
    )
    page = _FakeBlueprintPage("home")
    task = _FakeTask(project_id=project.id, blueprint_page_id=page.id, serp_config={"search_engine": "off"})
    ctx = _FakeCtx(_FakeDB(project, page), task)

    res = SerpStep().run(ctx)

    mock_fetch.assert_not_called()
    assert task.serp_data["source"] == "user_only"
    assert task.serp_data["urls"] == ["https://homepage-rival.com/x"]
    assert res.status == "completed"


@patch("app.services.pipeline.steps.serp_step.add_log")
@patch("app.services.pipeline.steps.serp_step.fetch_serp_data")
def test_serp_step_engine_off_falls_back_to_project_urls(mock_fetch, mock_log) -> None:
    project = _FakeProject(
        competitor_urls=["https://fallback.example.com/page"],
        project_keywords={"clustered": {"home": {"page_title": "Home"}}},
    )
    page = _FakeBlueprintPage("home")
    task = _FakeTask(project_id=project.id, blueprint_page_id=page.id, serp_config={"search_engine": "off"})
    ctx = _FakeCtx(_FakeDB(project, page), task)

    SerpStep().run(ctx)

    mock_fetch.assert_not_called()
    assert task.serp_data["urls"] == ["https://fallback.example.com/page"]


@patch("app.services.pipeline.steps.serp_step.add_log")
@patch("app.services.pipeline.steps.serp_step.fetch_serp_data")
def test_serp_step_google_engine_merges_per_page_urls_first(mock_fetch, mock_log) -> None:
    mock_fetch.return_value = {"source": "google", "urls": ["https://serp1.com/a", "https://serp2.com/b"]}
    project = _FakeProject(
        competitor_urls=["https://global.example.com"],
        project_keywords={"clustered": {"home": {"competitor_urls": ["https://my-page.com/x"]}}},
    )
    page = _FakeBlueprintPage("home")
    task = _FakeTask(project_id=project.id, blueprint_page_id=page.id, serp_config={"search_engine": "google"})
    ctx = _FakeCtx(_FakeDB(project, page), task)

    SerpStep().run(ctx)

    mock_fetch.assert_called_once()
    assert "https://my-page.com/x" in task.serp_data["urls"]
    assert "https://global.example.com" not in task.serp_data["urls"]
