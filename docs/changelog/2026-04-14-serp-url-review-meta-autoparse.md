# 14 апреля 2026 — SERP URL review: автопарсинг title/description + fallback в pipeline

**Дата:** 2026-04-14
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (закрыта):** при ручном добавлении URL в SERP review (`approve-serp-urls`) новые `organic_results` создавались с пустыми `title/description`, из-за чего переменные промптов `{{competitor_titles}}` и `{{competitor_descriptions}}` могли оставаться пустыми.

**Backend**
- **`app/services/scraper.py`**
  - `parse_html()` теперь извлекает `meta_title` (`<title>`) и `meta_description` (`<meta name="description">`, fallback `og:description`) вместе с прежними `headers/text/word_count`.
  - `scrape_urls()` прокидывает эти поля в `raw_results`, кэширует (`set_cached_scrape_item`) и возвращает агрегаты `scraped_titles` / `scraped_descriptions`.
  - Добавлен lightweight helper **`fetch_url_meta(url, timeout=12)`**: Serper scrape → fallback direct `requests.get`, безопасный возврат пустых строк при ошибке.
- **`app/api/tasks.py`**
  - Новый endpoint **`POST /api/tasks/fetch-url-meta`** с телом `{ "url": "https://..." }`.
  - Ответ: `{ "url", "title", "description", "domain" }`; при сетевых/парсинговых ошибках endpoint не падает 500, возвращает пустые `title/description`.
- **`app/services/pipeline.py`**
  - В `setup_vars()` после чтения SERP добавлен fallback: если `competitor_titles` / `competitor_descriptions` пусты, подставляются `scraped_titles` / `scraped_descriptions` из результата шага `competitor_scraping` (`step_results[competitor_scraping].result`).
  - В логи задачи пишутся warning-сообщения о fallback-источнике (`STEP_SCRAPING`).
  - `scrape_summary` дополнен полями `scraped_titles`, `scraped_descriptions`, `titles_source`, `descriptions_source` для дебага источника данных.

**Frontend**
- **`frontend/src/components/tasks/SerpUrlsReviewer.tsx`**
  - Для строки URL добавлены поля состояния `meta_loading` / `meta_error`.
  - При `Add URL`: строка появляется мгновенно (non-blocking UX), затем асинхронно вызывается `POST /tasks/fetch-url-meta`, и в строку подставляются `title/description/domain`.
  - Добавлена колонка **Description**.
  - Добавлена per-row кнопка обновления meta (`RefreshCw`, `animate-spin` во время запроса).
  - Добавлен snippet-предпросмотр в стиле Google (синий title, зелёный домен, серое описание с `line-clamp`).
- **`frontend/src/api/tasks.ts`**: новый метод `tasksApi.fetchUrlMeta(url)`.

**Поведение `approve-serp-urls`**
- Сохранено корректное «пересобирание» `organic_results` строго по `payload.urls`: удалённые URL не попадают в итоговый массив, добавленные получают новую запись (и затем могут быть обогащены meta через новый endpoint/UI).

---
