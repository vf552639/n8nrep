def test_settings_has_openai_oauth_fields():
    from app.config import settings
    assert hasattr(settings, "OPENAI_API_KEY")
    assert hasattr(settings, "OPENAI_OAUTH_DIR")
    assert hasattr(settings, "OPENAI_BASE_URL")
    # Default should be the user's standard codex dir
    assert settings.OPENAI_OAUTH_DIR.endswith(".codex") or settings.OPENAI_OAUTH_DIR == ""
    assert settings.OPENAI_BASE_URL == "https://api.openai.com/v1"
