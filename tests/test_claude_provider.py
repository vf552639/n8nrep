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
