from dataclasses import dataclass, field
from typing import Protocol

from app.services.pipeline.errors import PipelineError


@dataclass
class StepResult:
    status: str
    result: str | None = None
    model: str | None = None
    cost: float = 0.0
    variables_snapshot: dict | None = None
    resolved_prompts: dict | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class StepPolicy:
    retryable_errors: tuple[type[PipelineError], ...] = ()
    max_retries: int = 0
    skip_on: tuple[type[PipelineError], ...] = ()
    timeout_minutes: int | None = None


class PipelineStep(Protocol):
    name: str
    policy: StepPolicy

    def run(self, ctx: "PipelineContext") -> StepResult: ...
