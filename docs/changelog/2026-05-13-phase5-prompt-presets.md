# Phase 5 — Prompt Presets (13 May 2026)

Adds curated playbook tables (`prompt_presets`, `prompt_preset_items`) and a
new `site_projects.prompt_preset_id` FK. Pipeline now resolves
agent → prompt through the preset before falling back to `is_active=True`.

## Backend
- `app/models/prompt_preset.py` (new) — `PromptPreset` + `PromptPresetItem` with cascade-delete and unique `(preset_id, agent_name)`.
- `app/services/prompt_presets.py` (new) — `resolve_prompt_for_agent(db, agent_name, preset_id)` with the existing `content_fact_checking → fact_checking` fallback preserved.
- `app/api/prompt_presets.py` (new) + `app/schemas/prompt_preset.py` (new) — CRUD `/api/prompt-presets` with duplicate-agent guard via `model_validator`.
- `app/models/project.py` — `prompt_preset_id` FK on `SiteProject` (`SET NULL` on preset delete).
- `app/services/pipeline/llm_client.py` — `get_prompt_obj(db, agent_name, preset_id)` delegates to the new resolver; `call_agent` reads `ctx.prompt_preset_id`.
- `app/services/pipeline/context.py` — `PipelineContext.prompt_preset_id` loaded from the linked `SiteProject`.
- `app/schemas/project.py` + `app/api/projects.py` — `SiteProjectCreate.prompt_preset_id` round-trips through GET responses.

Migrations:
- `alembic/versions/g7h8i9j0k1l2_add_prompt_presets.py`
- `alembic/versions/h8i9j0k1l2m3_add_project_preset_fk.py`

## Frontend
- `frontend/src/types/promptPreset.ts` + `frontend/src/api/promptPresets.ts` (new).
- `frontend/src/types/project.ts` — `Project.prompt_preset_id`.
- `frontend/src/api/projects.ts` — `SiteProjectCreatePayload` / `SiteProjectDraftPayload` accept `prompt_preset_id`.
- `frontend/src/components/PromptPresetEditor.tsx` (new) — reusable form with agent → prompt overrides.
- `frontend/src/pages/PromptsPage.tsx` — collapsible **Prompt presets** section above the editor with new/edit/delete flows.
- `frontend/src/pages/ProjectsPage.tsx` — preset selector in the New Project modal (and round-tripped on draft edits).

## Tests
- `tests/test_prompt_preset_model.py` (model export + columns).
- `tests/test_prompt_presets_api.py` (CRUD: create/get/update/delete/duplicate-agent-422). Uses module-scoped SQLite under `tests/` to dodge the api/ conftest Postgres skip.
- `tests/services/test_prompt_presets.py` (resolver: preset hit, no preset, preset-with-missing-agent).
- `tests/test_project_preset_api.py` (`SiteProjectCreate.prompt_preset_id` persists on the `SiteProject` row).

## Notes for follow-up
- `tests/api/` (factory_boy + Postgres) remains gated by the existing conftest. Phase 5 desktop tests live under `tests/`.
- `PromptPresetEditor` lists prompts via `/api/prompts?active_only=false`; if the existing `/api/prompts` handler ignores `active_only`, the query still returns the full set since the parameter is benign.
- The pipeline `call_agent` only honours `ctx.prompt_preset_id` when the project row is present and has the FK; legacy task rows without a project keep the original active-prompt resolution.
