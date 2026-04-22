from app.services import _pipeline_legacy as legacy
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult


class _Step:
    name = "final_editing"
    policy = StepPolicy()

    def run(self, ctx):
        result, model, cost = legacy.phase_final_editing(ctx)
        return StepResult(status="completed", result=result, model=model, cost=cost)


register_step(_Step())
