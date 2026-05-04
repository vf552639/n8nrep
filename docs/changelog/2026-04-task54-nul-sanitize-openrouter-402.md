# Апрель 2026 — task54: NUL-санитизация и OpenRouter 402

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** на проектных страницах наблюдались (1) падения commit с `ValueError: ... NUL (0x00)` при записи scraped/serp данных в Postgres и (2) неэффективные повторы LLM-вызовов при OpenRouter `402 Payment Required` из-за слишком большого `max_tokens`.

**Сделано**
- Добавлен `app/utils/text_sanitize.py` с `strip_nul(value)` (рекурсивная очистка строк в `str/list/dict`).
- `app/services/scraper.py`: `parse_html()` и агрегаты `scrape_urls()` санитизируются через `strip_nul`; кэшированные записи scrape также проходят очистку.
- `app/services/pipeline/steps/serp_step.py`: перед записью `ctx.task.serp_data` выполняется `serp_data = strip_nul(serp_data)`.
- `app/services/pipeline/errors.py`: добавлен `InsufficientCreditsError(LLMError)`.
- `app/services/llm.py`: добавлен 402-branch — парсинг `can only afford N`, адаптивное снижение `max_tokens` (с margin), retry без sleep; при неразрешимом 402 — fail-fast через `InsufficientCreditsError`.
- `app/services/pipeline/llm_client.py`: отдельная обработка `InsufficientCreditsError` (re-raise) и лог события downscale.
- Добавлены тесты: `tests/unit/test_text_sanitize.py`, `tests/services/test_llm_402_downscale.py`.

---
