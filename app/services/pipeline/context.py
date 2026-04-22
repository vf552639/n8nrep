from app.services import _pipeline_legacy as legacy
from app.services.pipeline.persistence import completed_step_body
from app.services.pipeline_constants import (
    STEP_FINAL_ANALYSIS,
    STEP_HTML_STRUCT,
    STEP_META_GEN,
    STEP_PRIMARY_GEN,
    STEP_SERP,
)


class PipelineContext(legacy.PipelineContext):
    """Pipeline context with typed helpers for completed step outputs."""

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
