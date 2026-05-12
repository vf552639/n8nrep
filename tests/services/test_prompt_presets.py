"""Phase 5: preset-aware prompt resolution. Uses an isolated SQLite per module."""
import os
import sys

import pytest


@pytest.fixture(scope="module", autouse=True)
def _desktop_env(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("p5_resolve") / "db.sqlite"
    os.environ["AUTH_DISABLED"] = "true"
    os.environ["DESKTOP_MODE"] = "true"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    saved = {name: mod for name, mod in sys.modules.items() if name == "app" or name.startswith("app.")}
    for name in list(saved):
        sys.modules.pop(name, None)
    from app.main import _run_desktop_migrations
    _run_desktop_migrations()
    yield
    for name in [n for n in sys.modules if n == "app" or n.startswith("app.")]:
        if name not in saved:
            sys.modules.pop(name, None)
    for name, mod in saved.items():
        sys.modules[name] = mod


@pytest.fixture
def db_session():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seed_prompts(db_session):
    """Create one active prompt + one inactive prompt for `primary_generation`."""
    from app.models.prompt import Prompt
    from app.models.prompt_preset import PromptPreset, PromptPresetItem
    # Clean any prior preset rows so resolver behavior is deterministic across tests.
    db_session.query(PromptPresetItem).delete()
    db_session.query(PromptPreset).delete()
    db_session.query(Prompt).filter(Prompt.agent_name == "primary_generation").delete()
    db_session.commit()

    active = Prompt(
        agent_name="primary_generation",
        system_prompt="active",
        user_prompt="",
        model="openai/gpt-5",
        is_active=True,
    )
    alt = Prompt(
        agent_name="primary_generation",
        system_prompt="alt",
        user_prompt="",
        model="openai/gpt-5-mini",
        is_active=False,
    )
    db_session.add_all([active, alt])
    db_session.commit()
    db_session.refresh(active)
    db_session.refresh(alt)
    return {"active_primary": active, "alt_primary": alt}


def test_resolve_returns_preset_prompt_when_set(db_session, seed_prompts):
    from app.models.prompt_preset import PromptPreset, PromptPresetItem
    from app.services.prompt_presets import resolve_prompt_for_agent

    alt = seed_prompts["alt_primary"]
    preset = PromptPreset(name="alt-preset")
    db_session.add(preset)
    db_session.flush()
    db_session.add(
        PromptPresetItem(
            preset_id=preset.id,
            agent_name="primary_generation",
            prompt_id=alt.id,
        )
    )
    db_session.commit()

    resolved = resolve_prompt_for_agent(
        db_session, agent_name="primary_generation", preset_id=preset.id
    )
    assert resolved.id == alt.id


def test_resolve_falls_back_to_active(db_session, seed_prompts):
    from app.services.prompt_presets import resolve_prompt_for_agent

    active = seed_prompts["active_primary"]
    resolved = resolve_prompt_for_agent(
        db_session, agent_name="primary_generation", preset_id=None
    )
    assert resolved.id == active.id


def test_resolve_skip_preset_falls_through_for_missing_agent(db_session, seed_prompts):
    from app.models.prompt_preset import PromptPreset
    from app.services.prompt_presets import resolve_prompt_for_agent

    preset = PromptPreset(name="empty-preset")
    db_session.add(preset)
    db_session.commit()

    active = seed_prompts["active_primary"]
    resolved = resolve_prompt_for_agent(
        db_session, agent_name="primary_generation", preset_id=preset.id
    )
    assert resolved.id == active.id
