"""
Minimal HTTP 200 checks for each API router (task36 §1.4).

Requires Postgres (TEST_DATABASE_URL or SUPABASE_DB_URL) and reachable from the test host;
otherwise session fixtures skip these tests. CI provides Postgres and sets SUPABASE_DB_URL.

The app root ``GET /`` is covered in ``test_app_routes.py`` (14th entrypoint alongside 13
``include_router`` modules in ``app/main.py``).
"""

from __future__ import annotations

import pytest

# One lightweight GET per router under ``/api/*`` (see ``app/main.py``).
ROUTER_SMOKE_GETS = [
    ("/api/dashboard/stats", ("tasks", "sites")),
    ("/api/dashboard/queue", ("celery_workers_online",)),
    ("/api/tasks/", ("items", "total")),
    ("/api/articles/", None),  # list of objects
    ("/api/sites/", None),
    ("/api/templates/", None),
    ("/api/legal-pages/", None),
    ("/api/authors/", None),
    ("/api/prompts/", None),
    ("/api/settings/", None),  # dict (possibly empty if no .env)
    ("/api/blueprints/", None),
    ("/api/projects/", None),
    ("/api/health/worker", ("status",)),
    ("/api/health/serp", ("dataforseo", "serpapi")),
    ("/api/logs/", ("logs",)),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path,expected_keys", ROUTER_SMOKE_GETS)
async def test_router_get_smoke_200(path, expected_keys, async_api_client):
    r = await async_api_client.get(path)
    assert r.status_code == 200, f"{path}: {r.text[:500]}"
    body = r.json()
    if expected_keys is not None:
        for k in expected_keys:
            assert k in body, f"{path}: missing key {k!r} in {body!r}"
    else:
        assert isinstance(body, list | dict), f"{path}: expected list or dict, got {type(body)}"
