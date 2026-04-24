from unittest.mock import patch

from app.services.llm import fallbacks_for_model, timeout_for_model


def test_timeout_for_model_default():
    with patch("app.services.llm.settings") as s:
        s.LLM_MODEL_TIMEOUTS = ""
        s.LLM_REQUEST_TIMEOUT = 600
        assert timeout_for_model("openai/gpt-5-mini") == 600


def test_timeout_for_model_override():
    with patch("app.services.llm.settings") as s:
        s.LLM_MODEL_TIMEOUTS = "openai/gpt-5-mini=900,foo=12"
        s.LLM_REQUEST_TIMEOUT = 600
        assert timeout_for_model("openai/gpt-5-mini") == 900
        assert timeout_for_model("other") == 600


def test_fallbacks_for_model_empty():
    with patch("app.services.llm.settings") as s:
        s.LLM_MODEL_FALLBACKS = ""
        assert fallbacks_for_model("openai/gpt-5-mini") == []


def test_fallbacks_for_model_pipe_list_dedupes_primary():
    with patch("app.services.llm.settings") as s:
        s.LLM_MODEL_FALLBACKS = (
            "openai/gpt-5-mini=openai/gpt-5-mini|anthropic/claude-sonnet-4|anthropic/claude-sonnet-4"
        )
        assert fallbacks_for_model("openai/gpt-5-mini") == ["anthropic/claude-sonnet-4"]
