import pytest


def test_anthropic_importable():
    import anthropic  # noqa: F401
    assert True


def test_config_has_anthropic_key():
    from app.config import settings
    assert hasattr(settings, "ANTHROPIC_API_KEY")


def test_prompt_model_has_effort_and_fast_mode():
    from app.models.prompt import Prompt
    assert hasattr(Prompt, "effort")
    assert hasattr(Prompt, "fast_mode")


from unittest.mock import MagicMock, patch


def _make_mock_response(text: str, input_tokens: int = 100, output_tokens: int = 50):
    """Build a mock anthropic messages response."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = 0

    resp = MagicMock()
    resp.content = [block]
    resp.usage = usage
    return resp


def test_generate_text_claude_basic():
    """Routes correctly to Anthropic SDK with no thinking."""
    from app.services.llm_providers.claude import generate_text_claude

    mock_resp = _make_mock_response("Hello world")
    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_resp

        with patch("app.services.llm_providers.claude._get_client", return_value=instance):
            text, cost, model, usage = generate_text_claude(
                system_prompt="You are helpful.",
                user_prompt="Say hello",
                model="claude-haiku-4-5-20251001",
                effort="low",
                fast_mode=False,
            )

    assert text == "Hello world"
    assert model == "claude-haiku-4-5-20251001"
    assert cost > 0
    assert usage["prompt_tokens"] == 100


def test_generate_text_claude_thinking_enabled():
    """Adds thinking param when effort > low and model supports it."""
    from app.services.llm_providers.claude import generate_text_claude

    mock_resp = _make_mock_response("Deep thought")
    with patch("app.services.llm_providers.claude._get_client") as mock_get_client:
        instance = MagicMock()
        instance.messages.create.return_value = mock_resp
        mock_get_client.return_value = instance

        generate_text_claude(
            system_prompt="Think hard.",
            user_prompt="Solve it",
            model="claude-sonnet-4-6",
            effort="high",
            fast_mode=False,
        )

        call_kwargs = instance.messages.create.call_args[1]
        assert "thinking" in call_kwargs
        assert call_kwargs["thinking"]["budget_tokens"] == 10_000
        assert call_kwargs["temperature"] == 1.0


def test_generate_text_claude_fast_mode_disables_thinking():
    """fast_mode=True skips thinking even when effort=high."""
    from app.services.llm_providers.claude import generate_text_claude

    mock_resp = _make_mock_response("Fast answer")
    with patch("app.services.llm_providers.claude._get_client") as mock_get_client:
        instance = MagicMock()
        instance.messages.create.return_value = mock_resp
        mock_get_client.return_value = instance

        generate_text_claude(
            system_prompt="Be fast.",
            user_prompt="Quick question",
            model="claude-sonnet-4-6",
            effort="high",
            fast_mode=True,
        )

        call_kwargs = instance.messages.create.call_args[1]
        assert "thinking" not in call_kwargs


def test_generate_text_claude_haiku_no_thinking():
    """Haiku never gets thinking even with effort=extra_high."""
    from app.services.llm_providers.claude import generate_text_claude

    mock_resp = _make_mock_response("Haiku answer")
    with patch("app.services.llm_providers.claude._get_client") as mock_get_client:
        instance = MagicMock()
        instance.messages.create.return_value = mock_resp
        mock_get_client.return_value = instance

        generate_text_claude(
            system_prompt="System",
            user_prompt="User",
            model="claude-haiku-4-5-20251001",
            effort="extra_high",
            fast_mode=False,
        )

        call_kwargs = instance.messages.create.call_args[1]
        assert "thinking" not in call_kwargs
