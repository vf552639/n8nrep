import pytest


def test_anthropic_importable():
    import anthropic  # noqa: F401
    assert True


def test_config_has_anthropic_key():
    from app.config import settings
    assert hasattr(settings, "ANTHROPIC_API_KEY")
