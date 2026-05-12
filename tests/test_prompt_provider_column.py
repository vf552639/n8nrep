def test_prompt_has_provider_column():
    from app.models.prompt import Prompt
    assert hasattr(Prompt, "provider")
    col = Prompt.__table__.c["provider"]
    assert col.nullable is False
    assert col.server_default.arg == "openrouter"


def test_valid_providers():
    from app.services.llm_providers import VALID_PROVIDERS
    assert VALID_PROVIDERS == {"openrouter", "anthropic", "openai_codex", "perplexity"}
