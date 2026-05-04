# Март 2026 — SERP/Scraping cache (актуализация)

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

- `fetch_serp_data()` обёрнут в Redis-кэш финального результата (`_from_cache` пробрасывается в `step_results.serp_research.result`).
- `scrape_urls()` использует Redis-кэш per-URL и возвращает `cache_hits` / `cache_misses` в summary шага.
- Новые настройки в `config/.env`: `SERP_CACHE_ENABLED`, `SERP_CACHE_TTL`, `SCRAPE_CACHE_TTL`.

**Frontend — `StepCard.tsx` и модули `components/tasks/steps/`:**
- **`serp_research`** — `SerpStepView.tsx`: метрики (source, organic, PAA, related, featured snippet), бейджи `serp_features`, таблица URL, ссылка на `GET /api/tasks/{id}/serp-export` (ZIP).
- **`competitor_scraping`** — `ScrapingStepView.tsx`: метрики (из SERP, спарсено, ошибки, avg words, Serper), таблица `failed_results`, бейджи доменов.
- **Остальные шаги (LLM)** — `LlmStepView.tsx`: табы **Result** / **Prompts** / **Variables** (`resolved_prompts`, `variables_snapshot`, цвет строк переменных пустых/заполненных).
- **`ExcludeWordsAlert`** при наличии `exclude_words_violations` на шаге.
- Парсинг `step.result` из JSON-строки или объекта — `parseStepResult.ts`.

**Layout (глобально):**
- Сворачиваемый **`Sidebar`**: ширина развёрнут `w-56`, свёрнут `w-[72px]`, только иконки + `title`; состояние в **`localStorage`** (`sidebar_collapsed`); кнопка в шапке сайдбара; `transition-all duration-300`. Состояние поднимается в **`MainLayout`**.

**Страница Prompts (дополнительно к разделу выше):**
- Блок Model Settings на **полную ширину** контентной колонки (выравнивание с трёхколоночным layout); без отдельного спейсера 240px.

---
