"""OpenRouter 402 affordance handling in generate_text (task54)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm import generate_text
from app.services.pipeline.errors import InsufficientCreditsError


def _ok_raw_response():
    raw = MagicMock()
    raw.text = '{"usage":{"cost":0.0}}'
    raw.headers = {}
    pr = MagicMock()
    msg = MagicMock()
    msg.content = "ok-body"
    ch = MagicMock()
    ch.message = msg
    pr.choices = [ch]
    pr.model = "openai/gpt-test"
    us = MagicMock()
    us.prompt_tokens = 1
    us.completion_tokens = 1
    us.total_tokens = 2
    pr.usage = us
    raw.parse.return_value = pr
    return raw


@pytest.fixture(autouse=True)
def _reset_openai_singleton():
    import app.services.llm as llm_mod

    llm_mod._openai_client = None
    yield
    llm_mod._openai_client = None


def test_402_downscales_max_tokens_on_retry():
    client = MagicMock()
    err = Exception(
        "Error code: 402 - You requested up to 65536 tokens, but can only afford 53233"
    )
    raw_ok = _ok_raw_response()
    client.chat.completions.with_raw_response.create.side_effect = [err, raw_ok]

    captured = []

    def _cb(event, payload):
        captured.append((event, payload))

    with patch("app.services.llm.get_openai_client", return_value=client):
        text, *_ = generate_text(
            "sys",
            "user",
            model="m",
            max_tokens=65536,
            max_retries=2,
            progress_callback=_cb,
        )

    assert text == "ok-body"
    assert client.chat.completions.with_raw_response.create.call_count == 2
    second_kw = client.chat.completions.with_raw_response.create.call_args_list[1].kwargs
    assert second_kw["max_tokens"] == 53233 - 256
    downscale_events = [p for e, p in captured if e == "max_tokens_downscale"]
    assert len(downscale_events) == 1
    assert downscale_events[0]["old_max_tokens"] == 65536
    assert downscale_events[0]["new_max_tokens"] == 53233 - 256


def test_402_fail_fast_when_affordance_too_low_for_floor():
    client = MagicMock()
    err = Exception(
        "Error code: 402 - You requested up to 8000 tokens, but can only afford 500"
    )
    client.chat.completions.with_raw_response.create.side_effect = [err]

    with patch("app.services.llm.get_openai_client", return_value=client):
        with pytest.raises(InsufficientCreditsError):
            generate_text("s", "u", model="m", max_tokens=8000, max_retries=2)

    assert client.chat.completions.with_raw_response.create.call_count == 1


def test_402_fail_fast_without_affordance_number():
    client = MagicMock()
    client.chat.completions.with_raw_response.create.side_effect = [
        Exception("Error code: 402 - Payment Required")
    ]

    with patch("app.services.llm.get_openai_client", return_value=client):
        with pytest.raises(InsufficientCreditsError):
            generate_text("s", "u", model="m", max_tokens=1000, max_retries=2)

    assert client.chat.completions.with_raw_response.create.call_count == 1
