from sqlalchemy.orm import Session

from app.models.blueprint import BlueprintPage
from app.models.site import Site
from app.models.task import Task
from app.services.pipeline.persistence import completed_step_body
from app.services.pipeline_constants import (
    STEP_FINAL_ANALYSIS,
    STEP_HTML_STRUCT,
    STEP_META_GEN,
    STEP_PRIMARY_GEN,
    STEP_SERP,
)
from app.services.pipeline_presets import pipeline_steps_use_serp, resolve_pipeline_steps


class PipelineContext:
    def __init__(self, db: Session, task_id: str, auto_mode: bool = False):
        self.db = db
        self.task_id = task_id
        self.auto_mode = auto_mode

        self.task = db.query(Task).filter(Task.id == task_id).first()
        if not self.task:
            raise ValueError(f"Task {task_id} not found")

        self.site = db.query(Site).filter(Site.id == self.task.target_site_id).first()
        self.site_name = self.site.name if self.site else "Unknown Site"

        self.blueprint_page = None
        self.all_site_pages = []
        self.page_slug = ""
        self.page_title = ""
        self.use_serp = True
        self.pipeline_steps = None

        if self.task.blueprint_page_id:
            self.blueprint_page = (
                db.query(BlueprintPage).filter(BlueprintPage.id == self.task.blueprint_page_id).first()
            )
            if self.blueprint_page:
                self.page_slug = self.blueprint_page.page_slug
                self.page_title = self.blueprint_page.page_title
                self.pipeline_steps = resolve_pipeline_steps(self.blueprint_page)
                self.use_serp = pipeline_steps_use_serp(self.pipeline_steps)

                bid = self.blueprint_page.blueprint_id
                all_pages_db = (
                    db.query(BlueprintPage)
                    .filter(BlueprintPage.blueprint_id == bid)
                    .order_by(BlueprintPage.sort_order)
                    .all()
                )
                self.all_site_pages = [
                    {"slug": p.page_slug, "title": p.page_title, "type": p.page_type, "url": p.filename}
                    for p in all_pages_db
                ]

        self.analysis_vars = {}
        self.template_vars = {}
        self.outline_data = self.task.outline or {}
        self.step_deadline: float | None = None

    def step_output(self, key: str) -> str:
        return completed_step_body(self.task, key)

    @property
    def serp(self) -> str:
        return self.step_output(STEP_SERP)

    @property
    def outline(self) -> str:
        return self.step_output(STEP_FINAL_ANALYSIS)

    @property
    def draft(self) -> str:
        return self.step_output(STEP_PRIMARY_GEN)

    @property
    def html(self) -> str:
        return self.step_output(STEP_HTML_STRUCT)

    @property
    def meta_raw(self) -> str:
        return self.step_output(STEP_META_GEN)
