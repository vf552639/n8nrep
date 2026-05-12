from unittest.mock import patch


def test_dispatch_routes_to_openrouter_by_default():
    from app.services.llm import dispatch_llm
    with patch("app.services.llm.generate_text") as gt:
        gt.return_value = (
            "hello",
            0.001,
            "openai/gpt-5",
            {"prompt_tokens": 10, "completion_tokens": 5},
        )
        text, cost, model, usage = dispatch_llm(
            provider="openrouter",
            system_prompt="s",
            user_prompt="u",
            model="openai/gpt-5",
            temperature=0.7,
            max_tokens=100,
            timeout=60,
            effort="low",
            fast_mode=False,
        )
        assert gt.called
        assert text == "hello"
        assert model == "openai/gpt-5"


def test_dispatch_routes_to_anthropic():
    from app.services.llm import dispatch_llm
    with patch("app.services.llm_providers.claude.generate_text_claude") as gtc:
        gtc.return_value = (
            "yo",
            0.002,
            "claude-sonnet-4-6",
            {"prompt_tokens": 7, "completion_tokens": 3},
        )
        dispatch_llm(
            provider="anthropic",
            system_prompt="s",
            user_prompt="u",
            model="claude-sonnet-4-6",
            temperature=0.7,
            max_tokens=100,
            timeout=60,
            effort="high",
            fast_mode=False,
        )
        kwargs = gtc.call_args.kwargs
        assert kwargs["effort"] == "high"
        assert kwargs["fast_mode"] is False


def test_dispatch_routes_to_openai_codex():
    from app.services.llm import dispatch_llm
    with patch("app.services.llm_providers.openai_codex.generate_text_codex") as gtc:
        gtc.return_value = (
            "yo",
            0.003,
            "gpt-5",
            {"prompt_tokens": 5, "completion_tokens": 2},
        )
        dispatch_llm(
            provider="openai_codex",
            system_prompt="s",
            user_prompt="u",
            model="gpt-5",
            temperature=0.7,
            max_tokens=100,
            timeout=60,
            effort="low",
            fast_mode=False,
        )
        kwargs = gtc.call_args.kwargs
        assert kwargs["model"] == "gpt-5"
        assert "effort" not in kwargs  # codex provider does not consume effort
