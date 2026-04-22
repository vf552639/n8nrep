from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult


class _DocxStep:
    name = "docx_export"
    policy = StepPolicy()

    def run(self, ctx):
        return StepResult(status="skipped", result=None, model=None, cost=0.0)


register_step(_DocxStep())
