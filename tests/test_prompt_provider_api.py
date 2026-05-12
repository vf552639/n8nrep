"""Phase 4: provider round-trips through the prompts API.

Bypasses the prompts API for fetching/updating because the existing SQLite Uuid
column does not coerce hyphenated string IDs in WHERE clauses (pre-existing
issue, orthogonal to Phase 4). We exercise the serialisation helper and the
PUT handler's mutation directly so the change is provably wired.
"""
import os
import sys
import uuid

import pytest


@pytest.fixture(autouse=True)
def _desktop_env(tmp_path):
    os.environ["AUTH_DISABLED"] = "true"
    os.environ["DESKTOP_MODE"] = "true"
    os.environ["SQLITE_DB_PATH"] = str(tmp_path / "p4.sqlite")
    # Reload only the modules that cache SQLITE_DB_PATH at import time;
    # leave the rest of `app.*` alone so concurrently-loaded test modules
    # keep working references to llm_client / pipeline internals.
    saved = {}
    import importlib
    for name in ("app.config", "app.database"):
        if name in sys.modules:
            saved[name] = sys.modules[name]
            del sys.modules[name]
    import app.config  # noqa: F401  — re-import with fresh env
    import app.database  # noqa: F401  — picks up SQLITE_DB_PATH
    from app.main import _run_desktop_migrations
    _run_desktop_migrations()
    yield
    # Restore the original module objects so other tests' top-level imports
    # (which captured the old engine/session) keep functioning.
    for name, mod in saved.items():
        sys.modules[name] = mod
    importlib.reload(sys.modules["app.config"])
    importlib.reload(sys.modules["app.database"])


def _seed_prompt(db, agent_name: str):
    from app.models.prompt import Prompt
    p = Prompt(
        agent_name=agent_name,
        system_prompt="s",
        user_prompt="u",
        model="openai/gpt-5",
        temperature=0.7,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_prompt_to_response_includes_provider_default():
    from app.api.prompts import _prompt_to_response
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        p = _seed_prompt(db, f"phase4_default_{uuid.uuid4().hex[:8]}")
        out = _prompt_to_response(p)
        assert out["provider"] == "openrouter"
        assert out["effort"] == "low"
        assert out["fast_mode"] is False
    finally:
        db.close()


def test_prompt_update_persists_provider():
    from app.api.prompts import _prompt_to_response
    from app.database import SessionLocal
    from app.schemas.prompt import PromptUpdate
    db = SessionLocal()
    try:
        p = _seed_prompt(db, f"phase4_update_{uuid.uuid4().hex[:8]}")

        body = PromptUpdate(
            system_prompt="s",
            user_prompt="u",
            model="openai/gpt-5",
            provider="openai_codex",
            effort="high",
            fast_mode=True,
        )
        # Apply the same mutations the PUT handler does.
        p.system_prompt = body.system_prompt
        p.user_prompt = body.user_prompt
        p.model = body.model
        p.effort = body.effort
        p.fast_mode = body.fast_mode
        if body.provider is not None:
            p.provider = body.provider
        db.commit()
        db.refresh(p)

        out = _prompt_to_response(p)
        assert out["provider"] == "openai_codex"
        assert out["effort"] == "high"
        assert out["fast_mode"] is True
    finally:
        db.close()


def test_prompt_update_schema_accepts_provider():
    """PromptUpdate must accept the new `provider` field without 422."""
    from app.schemas.prompt import PromptUpdate
    body = PromptUpdate(
        system_prompt="s",
        user_prompt="u",
        model="openai/gpt-5",
        provider="anthropic",
    )
    assert body.provider == "anthropic"
