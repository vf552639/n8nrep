"""Phase 5: CRUD /api/prompt-presets. Tests live under tests/ (not tests/api/)
because the api/ conftest hard-skips when Postgres is unreachable; desktop
mode runs against SQLite."""
import os
import sys
import uuid

import pytest


@pytest.fixture(scope="module", autouse=True)
def _desktop_env(tmp_path_factory):
    """Bootstrap desktop SQLite once per module. Saves/restores the app.* module
    cache so downstream test modules that imported pipeline internals at the
    top level keep working references."""
    db_path = tmp_path_factory.mktemp("p5_presets") / "db.sqlite"
    os.environ["AUTH_DISABLED"] = "true"
    os.environ["DESKTOP_MODE"] = "true"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    saved = {name: mod for name, mod in sys.modules.items() if name == "app" or name.startswith("app.")}
    for name in list(saved):
        sys.modules.pop(name, None)
    from app.main import _run_desktop_migrations
    _run_desktop_migrations()
    yield
    # Restore the original module objects so other test modules' module-level
    # imports (`from app.x import Y`) keep their cached references valid.
    for name in [n for n in sys.modules if n == "app" or n.startswith("app.")]:
        if name not in saved:
            sys.modules.pop(name, None)
    for name, mod in saved.items():
        sys.modules[name] = mod


@pytest.fixture(autouse=True)
def _clean_preset_tables():
    """Each test starts with empty preset tables (prompts persist across the
    module because seed_prompt creates one per test)."""
    from app.database import SessionLocal
    from app.models.prompt_preset import PromptPreset, PromptPresetItem
    db = SessionLocal()
    try:
        db.query(PromptPresetItem).delete()
        db.query(PromptPreset).delete()
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seed_prompt():
    from app.database import SessionLocal
    from app.models.prompt import Prompt
    db = SessionLocal()
    try:
        p = Prompt(
            agent_name=f"primary_generation_{uuid.uuid4().hex[:6]}",
            system_prompt="x",
            user_prompt="",
            model="openai/gpt-5",
            temperature=0.7,
            is_active=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        prompt_id = str(p.id)
        return type("P", (), {"id": prompt_id})()
    finally:
        db.close()


def test_create_preset(client, seed_prompt):
    r = client.post(
        "/api/prompt-presets",
        json={
            "name": "default",
            "description": "Default playbook",
            "items": [{"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)}],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "default"
    assert len(body["items"]) == 1


def test_get_presets(client, seed_prompt):
    client.post(
        "/api/prompt-presets",
        json={
            "name": "p1",
            "items": [{"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)}],
        },
    )
    r = client.get("/api/prompt-presets")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "p1" in names


def test_update_preset_replaces_items(client, seed_prompt):
    c = client.post(
        "/api/prompt-presets",
        json={
            "name": "edit-me",
            "items": [{"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)}],
        },
    ).json()
    pid = c["id"]
    r = client.put(
        f"/api/prompt-presets/{pid}",
        json={
            "name": "edit-me",
            "items": [
                {"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)},
                {"agent_name": "final_editing", "prompt_id": str(seed_prompt.id)},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 2


def test_delete_preset(client, seed_prompt):
    pid = client.post(
        "/api/prompt-presets",
        json={
            "name": "tmp",
            "items": [{"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)}],
        },
    ).json()["id"]
    r = client.delete(f"/api/prompt-presets/{pid}")
    assert r.status_code == 204
    assert client.get(f"/api/prompt-presets/{pid}").status_code == 404


def test_duplicate_agent_in_preset_is_rejected(client, seed_prompt):
    r = client.post(
        "/api/prompt-presets",
        json={
            "name": "dup",
            "items": [
                {"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)},
                {"agent_name": "primary_generation", "prompt_id": str(seed_prompt.id)},
            ],
        },
    )
    assert r.status_code == 422
