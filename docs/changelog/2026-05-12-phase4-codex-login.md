# Phase 4 — ChatGPT / OpenAI Codex provider + login flow (12 May 2026)

Adds a new LLM provider routed by `Prompt.provider="openai_codex"`. Reads
`~/.codex/auth.json` (Codex CLI session) when present; falls back to
`OPENAI_API_KEY`. `/api/auth/codex/{status,login,logout}` powers a Codex
LoginPanel in the existing "LLM & Auth" tab in Settings; Electron spawns
`codex login` via IPC. Generic `dispatch_llm()` replaces Phase 3's
`route_to_provider()` and dispatches by `Prompt.provider` rather than by
model-name prefix.

Files touched:
- `app/services/llm_providers/openai_codex.py` (new)
- `app/services/auth/codex_oauth.py` (new)
- `app/api/auth_codex.py` (new)
- `app/schemas/auth.py` (new)
- `app/services/llm.py` — `dispatch_llm()`
- `app/services/pipeline/llm_client.py` — uses `dispatch_llm`
- `app/models/prompt.py` — `provider` column
- `app/api/prompts.py` / `app/schemas/prompt.py` — provider passthrough
- `alembic/versions/f6g7h8i9j0k1_add_prompt_provider.py`
- `electron/login_handlers.ts`, `electron/preload.ts`, `electron/main.ts`
- `frontend/src/components/LoginPanel.tsx` (new)
- `frontend/src/types/auth.ts`, `frontend/src/api/auth.ts` (new)
- `frontend/src/pages/SettingsPage.tsx` — Codex section in LLM & Auth tab
- `frontend/src/pages/PromptsPage.tsx` — provider/effort/fast_mode controls
- `frontend/src/types/prompt.ts`, `frontend/src/api/prompts.ts` — provider field

Tests:
- `tests/test_config_phase4.py`
- `tests/test_prompt_provider_column.py`
- `tests/services/test_codex_provider.py`
- `tests/services/test_llm_dispatch.py`
- `tests/test_auth_codex_api.py`
- `tests/test_prompt_provider_api.py`

Notes for follow-up:
- `tests/api/conftest.py` skips when Postgres is unreachable; desktop-mode
  Phase 4 tests live under `tests/` (not `tests/api/`) to avoid that skip.
- The perplexity branch of `dispatch_llm` imports a module added in Phase 6;
  the import is inside the `provider == "perplexity"` branch so it does
  not affect the current build until invoked.
- The existing SQLite `sa.Uuid` column refuses hyphenated string ids in
  WHERE clauses (`'str' object has no attribute 'hex'`). Affects PUT/GET on
  prompt routes when seeded via the API in desktop mode; the schema-level
  provider tests bypass this by exercising the helper + handler directly.
