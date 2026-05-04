# Апрель 2026 — task43: декомпозиция pipeline (A–E, F1–F10)

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** после выделения каркаса `app/services/pipeline/` и плана task42 выполнен основной перенос логики из `app/services/_pipeline_legacy.py` в пакет с шагами.

**A. Baseline e2e smoke**
- Добавлен `tests/services/test_pipeline_e2e_smoke.py` с `test_run_pipeline_full_preset_smoke` (full preset, 14 шагов, `GeneratedArticle`/status/step_results ассёрты).

**B. Удаление битых shim-шагов**
- Удалены старые `steps/*_step.py` shim-файлы, которые пытались unpack `None` из `phase_*`.
- `steps/__init__.py` переведён на контролируемые импорты актуальных step-модулей.

**C–E. Перенос утилит и контекста**
- Реализованы реальные модули: `pipeline/persistence.py`, `pipeline/vars.py`, `pipeline/template_vars.py`, `pipeline/llm_client.py`, `pipeline/context.py`, `pipeline/assembly.py`.
- `PipelineContext` больше не наследуется от legacy.
- Сборка статьи вынесена в `finalize_article(ctx)` в `pipeline/assembly.py`.

**F1–F10. Перенос 21 phase-функции в step-классы**
- Добавлены step-файлы по доменам: `serp_step.py`, `outline_step.py`, `meta_step.py`, `html_assembly_step.py`, `final_editing_step.py`, `image_prompts_step.py`, `image_gen_step.py`, `image_inject_step.py`, `draft_step.py`, `legal_step.py`.
- В `legacy` добавлен `_legacy_phase_adapter(step_name)`: берёт step из `STEP_REGISTRY`, вызывает `run(ctx)` и сохраняет `StepResult` через `save_step_result`.
- `PHASE_REGISTRY` полностью переключён на `_legacy_phase_adapter(...)`; `def phase_*` в `legacy` удалены.
- `_auto_approve_images` перенесён в `steps/image_gen_step.py`; `run_pipeline` в `legacy` использует его оттуда.

**Результат текущего этапа**
- `STEP_REGISTRY` содержит все 21 pipeline-шага.
- В `app/services/pipeline/steps/*.py` нет файлов > 400 строк.
- Legacy-сценарий запуска сохранён (runner по-прежнему `legacy.run_pipeline`), но логика шагов уже выполняется через новый пакет.

---
