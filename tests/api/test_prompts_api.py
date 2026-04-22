from __future__ import annotations

import pytest

from tests.factories import PromptFactory


@pytest.mark.asyncio
async def test_prompts_list_active_only_default(async_api_client):
    r = await async_api_client.get("/api/prompts/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_prompts_list_include_inactive(async_api_client):
    r = await async_api_client.get("/api/prompts/?active_only=false")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_prompt_versions_and_put(async_api_client):
    p = PromptFactory(agent_name="unique_agent_versions_api")
    pid = str(p.id)

    vr = await async_api_client.get(f"/api/prompts/{pid}/versions")
    assert vr.status_code == 200
    assert isinstance(vr.json(), list)

    ur = await async_api_client.put(
        f"/api/prompts/{pid}",
        json={
            "system_prompt": "sys",
            "user_prompt": "usr",
            "model": "openai/gpt-4o-mini",
            "max_tokens": None,
            "max_tokens_enabled": False,
            "temperature": 0.7,
            "temperature_enabled": False,
            "frequency_penalty": 0.0,
            "frequency_penalty_enabled": False,
            "presence_penalty": 0.0,
            "presence_penalty_enabled": False,
            "top_p": 1.0,
            "top_p_enabled": False,
            "skip_in_pipeline": False,
        },
    )
    assert ur.status_code == 200
    assert ur.json()["system_prompt"] == "sys"


@pytest.mark.asyncio
async def test_create_prompt(async_api_client):
    r = await async_api_client.post(
        "/api/prompts/",
        json={
            "agent_name": "new_agent_api_test",
            "system_prompt": "s",
            "user_prompt": "u",
            "model": "openai/gpt-4o-mini",
            "max_tokens": 1000,
            "skip_in_pipeline": True,
        },
    )
    assert r.status_code == 200
    assert "id" in r.json()
