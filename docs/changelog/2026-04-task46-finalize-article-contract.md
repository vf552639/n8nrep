# Апрель 2026 — task46: контракт `finalize_article` + unit-тесты

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Сделано**
- `app/services/pipeline/assembly.py`:
  - `finalize_article(ctx)` приведён к «чистому» контракту: сборка + upsert + `task.status="completed"` + `db.commit()` + `return GeneratedArticle`;
  - удалены `try/except`, `db.rollback()`, перевод в `failed`, `error_log`, `notify_task_success/failed` внутри assembly;
  - выделены private helper-ы (`_extract_meta_with_fallback`, `_build_full_page`, `_apply_author_footer`, `_process_fact_check`, `_upsert_article`, `_save_dedup_anchors`).
- `app/services/pipeline/runner.py`:
  - success-ветка после `finalize_article(ctx)` теперь в runner: лог `✅ Pipeline finished successfully` и `notify_task_success(...)`;
  - error-handling остаётся единым в runner (`rollback`, `failed`, `notify_task_failed`).
- Добавлен `tests/services/test_finalize_article.py` (контрактные integration-тесты по happy/error/fallback/upsert/strict fact-check/no-notifier side effects).
- Обновлены monkeypatch-точки в smoke/e2e-тестах на нотификаторы runner.

**Статус**
- Контракт task46 закрыт: success/failure side-effects уровня pipeline централизованы в `runner.py`.

---
