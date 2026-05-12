# Phase 6 — Perplexity provider + per-prompt provider toggle (13 May 2026)

Wires the fourth provider behind `Prompt.provider="perplexity"` via
`dispatch_llm`. Adds `PERPLEXITY_API_KEY` and `PERPLEXITY_BASE_URL` to
`Settings`; Settings UI exposes the key under Integrations. Models commonly
chosen here: `sonar`, `sonar-pro`, `sonar-reasoning`, `sonar-deep-research`.

The provider uses the OpenAI SDK against
`https://api.perplexity.ai/chat/completions` — no separate HTTP client
needed. Cost is computed per-million tokens via a small in-memory table
(`_COST_PER_MTOK`); update the table when pricing changes.

Files:
- `app/services/llm_providers/perplexity.py` (new)
- `app/config.py`, `app/schemas/settings.py`, `.env.example`
- `frontend/src/pages/SettingsPage.tsx` — Perplexity field in Integrations + hint card in LLM & Auth

Tests:
- `tests/test_config_phase6.py`
- `tests/services/test_perplexity_provider.py`
- `tests/services/test_llm_dispatch.py::test_dispatch_routes_to_perplexity`

Notes for follow-up:
- The hint card in LLM & Auth uses a static reference to the Integrations tab (no in-page navigation button) because the inline `LlmAuthTab` component does not receive `setActiveTab`.
- Perplexity has no OAuth — it is API-key only. The hint card makes that explicit.
