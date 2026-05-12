from unittest.mock import MagicMock, patch


def _mock_chat_completion(text: str, prompt_tokens: int = 50, completion_tokens: int = 30):
    choice = MagicMock()
    choice.message.content = text
    usage = MagicMock(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    resp = MagicMock(choices=[choice], usage=usage, model="gpt-5")
    return resp


def test_generate_text_codex_uses_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_OAUTH_DIR", str(tmp_path / "no-codex"))
    # Force settings reload to pick up env
    import importlib
    from app import config as cfg
    importlib.reload(cfg)
    from app.services.llm_providers import openai_codex

    with patch.object(openai_codex, "_build_client") as build:
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_chat_completion("hi")
        build.return_value = client

        text, cost, model, usage = openai_codex.generate_text_codex(
            system_prompt="sys",
            user_prompt="hi",
            model="gpt-5",
            temperature=0.7,
            max_tokens=128,
            timeout=60,
        )
    assert text == "hi"
    assert model == "gpt-5"
    assert usage["prompt_tokens"] == 50
    assert cost > 0


def test_generate_text_codex_uses_codex_oauth_when_present(tmp_path, monkeypatch):
    import json
    oauth_dir = tmp_path / ".codex"
    oauth_dir.mkdir()
    (oauth_dir / "auth.json").write_text(
        json.dumps({"tokens": {"access_token": "oauth-tok", "account_id": "acc_1"}})
    )
    monkeypatch.setenv("OPENAI_OAUTH_DIR", str(oauth_dir))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import importlib
    from app import config as cfg
    importlib.reload(cfg)
    from app.services.llm_providers import openai_codex

    with patch("openai.OpenAI") as OpenAICls:
        instance = MagicMock()
        instance.chat.completions.create.return_value = _mock_chat_completion("hello")
        OpenAICls.return_value = instance

        openai_codex.generate_text_codex(
            system_prompt="s",
            user_prompt="u",
            model="gpt-5-codex",
            temperature=0.7,
            max_tokens=64,
            timeout=30,
        )
    call_kwargs = OpenAICls.call_args.kwargs
    assert call_kwargs["api_key"] == "oauth-tok"
    assert "X-Codex-Account-Id" in call_kwargs.get("default_headers", {})


def test_generate_text_codex_raises_when_no_creds(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_OAUTH_DIR", str(tmp_path / "missing"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import importlib
    from app import config as cfg
    importlib.reload(cfg)
    from app.services.llm_providers import openai_codex
    import pytest
    with pytest.raises(ValueError, match="No OpenAI credentials"):
        openai_codex.generate_text_codex(
            system_prompt="s",
            user_prompt="u",
            model="gpt-5",
            temperature=0.7,
            max_tokens=10,
            timeout=30,
        )
