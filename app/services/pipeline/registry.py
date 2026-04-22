from app.services.pipeline.steps.base import PipelineStep
from app.services.pipeline_presets import resolve_pipeline_steps

STEP_REGISTRY: dict[str, PipelineStep] = {}


def register_step(step: PipelineStep) -> PipelineStep:
    STEP_REGISTRY[step.name] = step
    return step


def resolve_pipeline_steps_from_preset(blueprint_page):
    return resolve_pipeline_steps(blueprint_page)
