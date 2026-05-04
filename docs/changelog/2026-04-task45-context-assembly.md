# Апрель 2026 — task45 (Шаг 4): Context + Assembly, статус

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Сделано**
- `PipelineContext` теперь определяется в `app/services/pipeline/context.py` (конструктор + геттеры `step_output` / `serp` / `outline` / `draft` / `html` / `meta_raw`).
- `run_pipeline` в `app/services/pipeline/runner.py` завершает пайплайн через `finalize_article(ctx)` из `app/services/pipeline/assembly.py`.
- В `assembly.py` используются живые helper-ы `pick_structured_html_for_assembly` / `pick_html_for_meta` и `completed_step_body`.
- Для стабильности monkeypatch-тестов в `app/services/pipeline/__init__.py` добавлены/расширены реэкспорты: `settings`, `generate_text`, `fetch_serp_data`, `scrape_urls`, `notify_task_success`, `notify_task_failed`, а также helper API пайплайна.

**Итог**
- Шаг 4 как структурный этап закрыт: `context` и `assembly` выделены, раннер использует `finalize_article`.
- Детали по финализации контракта и тестам вынесены в отдельный шаг task46.

---
