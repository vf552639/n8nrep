# 22 апреля 2026 — task42: план декомпозиции pipeline.py

**Дата:** 2026-04-22
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** `app/services/pipeline.py` разросся до **2579 строк** и совмещает пять несвязанных обязанностей: оркестрация, 21 phase-функция, построение `PipelineContext`, подготовку переменных, сборку `GeneratedArticle`. Цель — чисто структурный рефакторинг без изменения поведения.

**Целевая структура:** пакет `app/services/pipeline/` с модулями:
- `__init__.py` — публичный re-export (`run_pipeline`, `PipelineContext`, `apply_template_vars`)
- `context.py`, `registry.py`, `runner.py`, `assembly.py`, `persistence.py`, `vars.py`, `llm_client.py`, `errors.py`
- `steps/` — 12 файлов по доменам (serp, outline, image×3, draft, legal, final_editing, html_assembly, meta, docx-stub)

**Критерий готовности:** ни один файл > 400 строк; все тесты проходят; реальная задача воспроизводит артефакт.

**План (7 шагов, инкрементально):** инвентаризация/якорные тесты → пакет с legacy re-export → вынос persistence/vars/llm_client → base-interface/registry/errors → PipelineContext+assembly → перенос шагов по группам → новый runner + удаление legacy.

Подробный план — в **`task42.md`** в корне репозитория.

---
