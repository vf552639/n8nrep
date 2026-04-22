import threading
import time

import pytest

from app.services.pipeline.context import PipelineContext
from app.services.pipeline.errors import StepTimeoutError
from app.services.pipeline.runner import _call_with_timeout
from app.services.pipeline.steps.base import StepPolicy, StepResult


class _SleepStep:
    name = "slow"
    policy = StepPolicy()

    def run(self, ctx: PipelineContext) -> StepResult:
        time.sleep(2.0)
        return StepResult(status="completed", result="ok", model="m", cost=0.0)


def test_call_with_timeout_raises_step_timeout_error_main_thread():
    step = _SleepStep()
    with pytest.raises(StepTimeoutError, match="timed out"):
        _call_with_timeout(step, None, timeout_sec=1)


def test_call_with_timeout_raises_from_worker_thread():
    step = _SleepStep()
    errors: list[BaseException] = []

    def worker():
        try:
            _call_with_timeout(step, None, timeout_sec=1)
        except BaseException as e:
            errors.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5)
    assert not t.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], StepTimeoutError)
