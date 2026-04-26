"""Regression: DB errors inside LLM progress callbacks must not poison the session (task59)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.services.pipeline.llm_client import call_agent


@pytest.fixture()
def pipeline_ctx():
    db = MagicMock(name="db")
    db.rollback = MagicMock()
    db.commit = MagicMock()
    task = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        step_results={},
        last_heartbeat=None,
    )
    ctx = SimpleNamespace(db=db, task=task, template_vars=None)
    return ctx


def test_call_agent_survives_callback_db_error(pipeline_ctx):
    """OperationalError in progress callback is suppressed; generate_text completes; session rolled back."""
    ctx = pipeline_ctx
    prompt = SimpleNamespace(
        agent_name="reader_opinion",
        skip_in_pipeline=False,
        system_prompt="sys",
        user_prompt="user",
        model="openai/gpt-5-mini",
        temperature_enabled=False,
        temperature=0.7,
        frequency_penalty_enabled=False,
        frequency_penalty=0.0,
        presence_penalty_enabled=False,
        presence_penalty=0.0,
        top_p_enabled=False,
        top_p=1.0,
        max_tokens_enabled=False,
        max_tokens=None,
    )

    add_log_calls: list[str] = []
    _fail_response_once = {"done": False}

    def add_log_side_effect(db, task, msg, **kwargs):
        s = str(msg)
        add_log_calls.append(s)
        if "LLM response received" in s and not _fail_response_once["done"]:
            _fail_response_once["done"] = True
            raise OperationalError("SSL SYSCALL error: EOF detected", None, None)

    def fake_generate_text(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback(
                "response_received",
                {
                    "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                    "cost": 0.001,
                    "model": "openai/gpt-5-mini",
                },
            )
            progress_callback(
                "retry_wait",
                {
                    "attempt": 1,
                    "max_retries": 2,
                    "reason": "mock",
                    "sleep_seconds": 0,
                },
            )
        return ("final-text", 0.01, "openai/gpt-5-mini", {})

    with (
        patch("app.services.pipeline.llm_client.get_prompt_obj", return_value=prompt),
        patch("app.services.pipeline.llm_client.add_log", side_effect=add_log_side_effect),
        patch("app.services.pipeline.llm_client.generate_text", side_effect=fake_generate_text),
    ):
        res, _cost, _model, _, _ = call_agent(ctx, "reader_opinion", "ctx", variables=None)

    assert res == "final-text"
    assert ctx.db.rollback.called
    assert any("LLM response received" in m for m in add_log_calls)
    assert any("Retry" in m for m in add_log_calls)
