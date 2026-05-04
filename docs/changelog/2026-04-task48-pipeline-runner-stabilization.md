# Апрель 2026 — task48: стабилизация pipeline runner + e2e smoke

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** после task47 оставались риски в policy/error-path и два «живых» дефекта в `tests/services/test_pipeline_e2e_smoke.py` (патч не в те bindings шагов и запуск без `auto_mode=True`, что приводило к `paused` на `serp_review`).

**Сделано**
- **Split vars/template_vars:** `setup_template_vars` перенесён из `app/services/pipeline/vars.py` в `app/services/pipeline/template_vars.py`; шаги и `app/services/pipeline/__init__.py` переведены на новый импорт.
- **Typed error mapping:** `app/services/pipeline/llm_client.py` теперь маппит ошибки `generate_text(...)` и отсутствие активного prompt в `LLMError` (`raise ... from e`).
- **Ошибки в шагах/assembly:**
  - `outline_step.py`: невалидный JSON от `final_structure_analysis` → `ParseError`;
  - `meta_step.py`: невалидный JSON от `meta_generation` → `ParseError`;
  - `assembly.py`: пустой assembled HTML → `ValidationError`; strict fact-check fail → `ValidationError`; невалидный `meta_generation` JSON → `ParseError`;
  - docstring `finalize_article()` обновлён под фактические типы исключений.
- **StepPolicy (runner-aware):**
  - `SerpStep`: `retryable_errors=(SerpError, LLMError), max_retries=1`;
  - `StructureFactCheckStep` и `ContentFactCheckStep`: `skip_on=(LLMError, ParseError)`;
  - LLM-генерирующие шаги (`draft/final_editing/legal`) подняты до `max_retries=2`.
- **e2e-smoke fixes (`tests/services/test_pipeline_e2e_smoke.py`):**
  - запуск `run_pipeline(..., auto_mode=True)`;
  - monkeypatch для `call_agent`/`call_agent_with_exclude_validation` перенесён на step-level bindings (`outline_step`, `draft_step`, `meta_step`, `html_assembly_step`, `image_prompts_step`, `final_editing_step`, `legal_step`), чтобы не утекать в реальный `generate_text`.
- **Новые тесты ошибок:** добавлен `tests/services/test_pipeline_errors.py`:
  - retry `LLMError` до успеха (3-я попытка при `max_retries=2`);
  - `ParseError` в fact-check шаге с `skip_on` → `skipped`, pipeline может продолжаться;
  - `ValidationError` из `finalize_article` → `task.status=failed` + `error_log`;
  - pause-инвариант: при `auto_mode=False` после SERP задача уходит в `paused` с `_pipeline_pause.reason="serp_review"`, `competitor_scraping` ещё не выполнен.

**Статус**
- Фиксы task48 закрывают критичные разрывы между policy и runtime-path, а также делают e2e-smoke корректным с точки зрения pause-семантики runner.

---
