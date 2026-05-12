def test_settings_has_perplexity_key():
    from app.config import settings
    assert hasattr(settings, "PERPLEXITY_API_KEY")
    assert settings.PERPLEXITY_BASE_URL == "https://api.perplexity.ai"


def test_settings_update_schema_allows_perplexity_key():
    from app.schemas.settings import SettingsUpdate
    SettingsUpdate(PERPLEXITY_API_KEY="pplx-test")
