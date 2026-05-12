def test_models_export_prompt_preset():
    from app.models import PromptPreset, PromptPresetItem  # noqa: F401


def test_preset_columns():
    from app.models.prompt_preset import PromptPreset, PromptPresetItem
    assert "name" in PromptPreset.__table__.c
    assert "is_default" in PromptPreset.__table__.c
    assert "prompt_id" in PromptPresetItem.__table__.c
    assert "agent_name" in PromptPresetItem.__table__.c
