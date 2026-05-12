from unittest.mock import MagicMock, patch


def _mock_resp(text="Hi from sonar", in_tok=80, out_tok=40):
    choice = MagicMock()
    choice.message.content = text
    usage = MagicMock(
        prompt_tokens=in_tok,
        completion_tokens=out_tok,
        total_tokens=in_tok + out_tok,
    )
    resp = MagicMock(choices=[choice], usage=usage, model="sonar-pro")
    return resp


def test_generate_text_perplexity_uses_api_key(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
    import importlib
    from app import config as cfg
    importlib.reload(cfg)
    from app.services.llm_providers import perplexity

    with patch("openai.OpenAI") as OpenAICls:
        instance = MagicMock()
        instance.chat.completions.create.return_value = _mock_resp()
        OpenAICls.return_value = instance

        text, cost, model, usage = perplexity.generate_text_perplexity(
            system_prompt="s",
            user_prompt="u",
            model="sonar-pro",
            temperature=0.7,
            max_tokens=200,
            timeout=60,
        )
    OpenAICls.assert_called_once()
    call_kwargs = OpenAICls.call_args.kwargs
    assert call_kwargs["api_key"] == "pplx-test"
    assert call_kwargs["base_url"] == "https://api.perplexity.ai"
    assert text == "Hi from sonar"
    assert usage["prompt_tokens"] == 80


def test_generate_text_perplexity_raises_without_key(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    import importlib
    from app import config as cfg
    importlib.reload(cfg)
    from app.services.llm_providers import perplexity
    import pytest
    with pytest.raises(ValueError, match="PERPLEXITY_API_KEY"):
        perplexity.generate_text_perplexity(
            system_prompt="s",
            user_prompt="u",
            model="sonar-pro",
            temperature=0.7,
            max_tokens=10,
            timeout=10,
        )
