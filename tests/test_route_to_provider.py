from unittest.mock import MagicMock, patch
import pytest


def _mock_claude_response():
    return ("claude result", 0.01, "claude-sonnet-4-6", {"prompt_tokens": 10, "completion_tokens": 5})


def _mock_openrouter_response():
    return ("openrouter result", 0.001, "openai/gpt-4o", {"prompt_tokens": 10, "completion_tokens": 5})


def test_route_to_provider_dispatches_claude():
    """Models starting with 'claude-' go to generate_text_claude."""
    from app.services.llm import route_to_provider

    with patch("app.services.llm_providers.claude.generate_text_claude", return_value=_mock_claude_response()) as mock_claude:
        result = route_to_provider(
            system_prompt="sys",
            user_prompt="usr",
            model="claude-sonnet-4-6",
            effort="low",
            fast_mode=False,
        )

    mock_claude.assert_called_once()
    assert result[2] == "claude-sonnet-4-6"


def test_route_to_provider_dispatches_openrouter():
    """Models with '/' go to generate_text (OpenRouter)."""
    from app.services.llm import route_to_provider

    with patch("app.services.llm.generate_text", return_value=_mock_openrouter_response()) as mock_or:
        result = route_to_provider(
            system_prompt="sys",
            user_prompt="usr",
            model="openai/gpt-4o",
            effort="low",
            fast_mode=False,
        )

    mock_or.assert_called_once()
    assert result[2] == "openai/gpt-4o"


def test_route_to_provider_does_not_pass_effort_to_openrouter():
    """effort/fast_mode are never forwarded to generate_text."""
    from app.services.llm import route_to_provider

    with patch("app.services.llm.generate_text", return_value=_mock_openrouter_response()) as mock_or:
        route_to_provider(
            system_prompt="sys",
            user_prompt="usr",
            model="openai/gpt-4o",
            effort="high",
            fast_mode=True,
            temperature=0.5,
        )

    call_kwargs = mock_or.call_args[1]
    assert "effort" not in call_kwargs
    assert "fast_mode" not in call_kwargs
    assert call_kwargs.get("temperature") == 0.5


def test_prompt_kwargs_includes_effort_and_fast_mode():
    """llm_sampling_kwargs_from_prompt returns effort + fast_mode from prompt."""
    from app.services.prompt_llm_kwargs import llm_sampling_kwargs_from_prompt

    prompt = MagicMock()
    prompt.temperature = 0.7
    prompt.temperature_enabled = False
    prompt.frequency_penalty = 0.0
    prompt.frequency_penalty_enabled = False
    prompt.presence_penalty = 0.0
    prompt.presence_penalty_enabled = False
    prompt.top_p = 1.0
    prompt.top_p_enabled = False
    prompt.max_tokens = None
    prompt.max_tokens_enabled = False
    prompt.effort = "medium"
    prompt.fast_mode = True

    result = llm_sampling_kwargs_from_prompt(prompt)
    assert result["effort"] == "medium"
    assert result["fast_mode"] is True
