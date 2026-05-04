# Апрель 2026 — task50: сверка плана после удаления legacy

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** после пуша финальных изменений по декомпозиции pipeline требовалась проверка `plan1.md` относительно фактического состояния `origin/main`.

**Подтверждено**
- `app/services/_pipeline_legacy.py` удалён; точка входа выполнения — `app/services/pipeline/runner.py`.
- Диспетчеризация шагов идёт через `STEP_REGISTRY`; остаточных импортов `_pipeline_legacy` / `legacy.phase_*` в runtime-path нет.
- Тестовое покрытие по декомпозиции закрыто файлами `tests/services/test_pipeline_smoke.py`, `test_pipeline_e2e_smoke.py`, `test_pipeline_errors.py`, `test_finalize_article.py`.
- Порог размера файлов в `app/services/pipeline/*.py` соблюдён (`vars.py` = 343 строки, остальные меньше).
- `app/services/pipeline/steps/docx_step.py` удалён (пустого step-файла больше нет).

**Итог follow-up (task50)**
- Внешний импорт приватного `_auto_approve_images` закрыт: helper перенесён в `runner.py` (commit `c11e092`).
- Назначение модулей `vars.py` и `template_vars.py` зафиксировано module-level docstring в коде.
- `docx_step.py` не возвращается: DOCX реализован как post-export (`docx_builder` + API export endpoints), а не runtime-step пайплайна — решение принято сознательно.

---
