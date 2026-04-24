# ТЕХНОЛОГИЧЕСКИЙ СТЕК

## Backend

**FastAPI** (v0.109.0+)
- Асинхронный REST API фреймворк
- Авто-документация Swagger на /docs
- Dependency Injection для DB sessions и auth
- **`app/main.py`**: глобальный обработчик необработанных исключений → ответ **500** всегда **`application/json`** с полем **`detail`** (и **`path`/`method`**), чтобы фронт не получал **`text/plain` «Internal Server Error»** и не показывал ложный «Network Error»; при старте через **`lifespan`** — **`verify_migrations()`** (сравнение ревизии БД с head Alembic, см. **`docs/CURRENT_STATUS.md`**, **16.04.2026**); инициализация логирования через **`app/logging_config.configure_logging`** (**`LOG_JSON`**, **`LOG_LEVEL`** из **`app/config.py`**, см. **`docs/CURRENT_STATUS.md`**, **19.04.2026 — Этап 1**)

**Python** (3.12)
- Основной язык backend и pipeline
- Docker образ: python:3.12-slim

**SQLAlchemy** (v2.0.25+)
- ORM для работы с PostgreSQL
- Модели с UUID PK, JSONB полями, ENUM types
- **`app/database.py` — `engine`**: **`pool_pre_ping`**, **`pool_recycle=300`**, **`pool_size` / `max_overflow` / `pool_timeout`**, **`connect_args`** с **`statement_timeout=600000`** (мс, 10 мин) на сессию — тяжёлые **`UPDATE`** с **`step_results`** не обрываются преждевременно (ранее **60000** мс давали **`OperationalError`** на длинных страницах проекта; см. **`docs/CURRENT_STATUS.md`**, **task53 E**, коммит **`e441738`**); меньше «зависших» соединений и **`idle in transaction`** на стороне Supavisor; зависимость **`get_db()`** делает **`rollback()`** при исключении после **`yield`** перед **`close()`**; опционально **`db_session()`** для commit/rollback вне FastAPI

**Alembic** (v1.13.1+)
- Миграции БД
- Цепочка ревизий в `alembic/versions/` (в т.ч. `meta_data` JSONB у `generated_articles`)
- Autogenerate из моделей SQLAlchemy
- **`alembic/env.py`**, онлайн-миграции: перед **`run_migrations`** на соединении выставляются **`SET LOCAL statement_timeout = '300s'`** и **`SET LOCAL lock_timeout = '15s'`** — DDL дольше ждёт лок и реже падает на коротком таймауте пулера; **`SET LOCAL`** ограничивает действие таймаутов текущей транзакцией и не затрагивает следующие соединения пула (taskco, 22.04.2026)

**Pydantic** (v2.6.1+) + **Pydantic Settings** (v2.2.1+)
- Валидация данных в API endpoints
- Загрузка конфигурации из .env
- **Request/response-схемы** вынесены в **`app/schemas/`** (апрель 2026, **19.04**, task36); роутеры **`app/api/`** импортируют модели (**`app/api/tasks.py`** — только **`from app.schemas.task import ...`**, без inline **`BaseModel`**, **22.04.2026** — см. **`docs/CURRENT_STATUS.md`**, **«22 апреля 2026 — Этап 1: доводка»**)

**Инструментарий разработки** (**`requirements-dev.txt`**, **апрель 2026**): pytest, pytest-asyncio, pytest-cov, httpx, factory-boy, freezegun, ruff, pre-commit; корневая конфигурация — **`pyproject.toml`**. В CI (**taskco, 22.04.2026**) включены **`ruff check app tests`**, **`ruff format --check app tests`** и порог покрытия **`pytest --cov-fail-under=55`** (см. **`.github/workflows/ci.yml`**); перед **`pytest`** на workflow накатывается **`alembic upgrade head`** на тестовую БД. **`pyproject.toml`**: глобальные игнорирования `B008` (FastAPI Depends), `RUF001`/`RUF002` (русский unicode), `SIM`-стиль; per-file-ignore `F403`/`F405` для `pipeline.py`; секция `[tool.coverage.report]` (`skip_empty`, `exclude_lines`). Taskco §5 (22.04): исправлено **1060** legacy ruff-нарушений в `app/` и `tests/` (347 авто-fix + 39 ручных).

**structlog** (в **`requirements.txt`**, **апрель 2026**)
- **`app/logging_config.py`** — structlog + stdlib logging; файл **`logs/app.log`** остаётся текстовым для **`/api/logs`**
- **`app/workers/celery_app.py`** — сигнал **`worker_process_init`** → **`logs/worker.log`**
- **`app/services/pipeline/persistence.py`** — `add_log()` формирует события через **`LogEvent`** + **`append_log_event`** (taskco, 22.04.2026; после удаления `app/services/_pipeline_legacy.py`)
- **`app/services/pipeline/runner.py`** — per-step wall-clock: **`ThreadPoolExecutor`** + **`future.result(timeout)`** → **`StepTimeoutError`** (вместо SIGALRM, **task52**); **`ctx.step_deadline`** для лимита exclude-retry в **`llm_client.call_agent_with_exclude_validation`**
- **`app/api/tasks.py`** / **`app/api/projects.py`** — чтение JSONB полей через **`read_log_events`** / **`read_step_results`**

**python-docx** (v1.1+)
- Серверная генерация **Word (.docx)** в `app/services/docx_builder.py`: экспорт **проекта** (`build_project_docx`), **одной статьи** (`build_single_article_docx`: шапка **H1** из мета, таблица Keyword / Word Count / **Title** / Description) и **задачи** (`build_task_export_docx`, в т.ч. черновик из `step_results`). Мета title/description/H1 и список вариантов для развёрнутой таблицы — через **`app/services/meta_parser.py`** (**`extract_meta_from_parsed`**, **`meta_variant_list`**) и **`clean_and_parse_json`** в **`_get_all_meta_from_task`**. Тело статьи для экспорта: при непустом **`GeneratedArticle.html_content`** — он; иначе **`resolve_export_body`** из **`app/services/html_export.py`** с тем же приоритетом шагов, что **`pick_structured_html_for_assembly`** в **`pipeline.py`** (в т.ч. **`image_inject`** и **`html_structure`** раньше **`final_editing`**) — см. **`docs/CURRENT_STATUS.md`**, **15.04.2026** / **19.04.2026** (раздел DOCX и HTML-экспорт).
- **Архитектурное решение (task50):** DOCX остаётся post-export слоем; отдельный `docx_step` в runtime pipeline не используется (N/A by design).

**HTML-экспорт (MODX / Source)** — `app/services/html_export.py`: **`resolve_export_body`**, **`clean_html_for_paste`** (BeautifulSoup **`html.parser`**, сохранение **`<!-- MEDIA: ... -->`**); API **`GET /api/tasks/{id}/export-html`**, **`GET /api/projects/{id}/export-html?mode=zip|concat`** — см. **`docs/CURRENT_STATUS.md`**, **19.04.2026**.

**JSON из ответов LLM** — `app/services/json_parser.py`: **`clean_and_parse_json(text, unwrap_keys=None)`** (размотка вложенного dict только при явном **`unwrap_keys`**, напр. для **`ai_structure_analysis`**); покрытие — **`tests/test_json_parser.py`** — см. **`docs/CURRENT_STATUS.md`**, **11.04.2026**.

**URL проекта и SERP (task41, 21.04)** — `app/services/url_utils.py`: **`normalize_url`**, **`domain_of`**, **`merge_urls_dedup_by_domain`** — нормализация и мерж **`site_projects.competitor_urls`** с органикой SERP в **`phase_serp`**; покрытие — **`tests/unit/test_url_utils.py`**, интеграционный сценарий в **`tests/services/test_pipeline_smoke.py`** — см. **`docs/CURRENT_STATUS.md`**, **«21 апреля 2026 — task41»**.

**Критичные переменные шагов** — `app/services/pipeline_constants.py`: словарь **`CRITICAL_VARS`** (обязательные плейсхолдеры для агента); **`CRITICAL_VARS_ALLOW_EMPTY`** — исключения, когда переменная должна быть в контексте, но может быть пустой (напр. **`legal_reference`** для **`primary_generation_legal`** при генерации без образца). Проверка в **`call_agent`** (`app/services/pipeline/llm_client.py`). См. **`docs/CURRENT_STATUS.md`**, **21.04.2026**. **`llm_client` (task52):** таймаут вызова через **`timeout_for_model(prompt.model)`**; в лог при **`response.model` ≠ запрошенной** — пометка fallback; **`call_agent_with_exclude_validation`** учитывает **`ctx.step_deadline`**.

**Мета из `meta_generation`** — `app/services/meta_parser.py`: **`extract_meta_from_parsed`**, **`meta_variant_list`** (ключи **`results`** / **`variants`** без учёта регистра, case-insensitive поля); тесты **`tests/test_meta_parser.py`**.

**Full-page HTML, meta в `<head>` и блок автора (task40, 20.04)** — `app/services/template_engine.py`: **`ensure_head_meta`**, **`render_author_footer`**; при финальной сборке статьи **`pipeline`** всегда вызывает **`ensure_head_meta`** после **`generate_full_page`** и при необходимости вставляет author-footer перед **`</body>`**; **`site_builder`** логирует предупреждение при пустом **`full_page_html`** и fallback на **`html_content`**; см. **`docs/CURRENT_STATUS.md`**, **«20 апреля 2026 — task40»**; unit-тесты — **`tests/services/test_template_engine.py`**.

## База данных

**Supabase (PostgreSQL)**
- Облачный PostgreSQL (уже использовался в n8n)
- Подключение через `SUPABASE_DB_URL` (psycopg2-binary)
- pgvector расширение доступно (для будущего RAG)

**Основные таблицы** (не исчерпывающий список):  
tasks (**`status`**: enum PostgreSQL **`task_status`** — **`pending`**, **`processing`**, **`completed`**, **`failed`**, **`stale`**, **`paused`** (миграция **`m9n0o1p2q3re`** — пауза SERP URL review для одиночных задач); **`celery_task_id`** String(64), index — миграция **`x9y8z7w6v5u4`**, revoke при stale/force-fail (**task52**, см. **`CURRENT_STATUS.md`**); **`serp_config`** — миграция **`c8f9a0b1d2e3`**, наследуется от проекта при постановке задач; **`log_events`** JSONB — журнал выполнения пайплайна (ранее **`logs`**, миграция **`t7u8v9w0x1yb`**, см. **`CURRENT_STATUS.md`**, **19.04.2026 — Этап 1**), generated_articles (**в т.ч. колонка `meta_data`** — полный JSON от `meta_generation`, в т.ч. формат **`{"results": [...]}`** с несколькими вариантами Title/Description/H1/Trigger), **sites** (**`template_id`** FK → **`templates`**, **`legal_info`** JSONB), **`templates`** (переиспользуемые HTML-оболочки: name, html_template, description, …), **`legal_page_templates`** (образцы для legal-генерации: **`name`**, **`page_type`**, **`content`**, **`content_format`** (**`text`**/**`html`**), **`variables`** JSONB, **`notes`**, **`UniqueConstraint(name, page_type)`**; колонка **`title`** удалена миграцией **`q3r4s5t6u7vc`**), **authors** (поле **`country_full`**, миграция **`u8v9w0x1y2zc`**), **prompts** (**в т.ч. булевы `max_tokens_enabled`, `temperature_enabled`, `frequency_penalty_enabled`, `presence_penalty_enabled`, `top_p_enabled`** — миграция **`k5m6n7o8p9qb`**), site_blueprints, **blueprint_pages** (**`pipeline_preset`**, **`pipeline_steps_custom`** JSONB — миграция **`l6m7n8o9p0qc`**; **`default_legal_template_id`** FK → **`legal_page_templates`** — миграция **`p2q3r4s5t6ub`**; порядок шагов задачи резолвится в **`app/services/pipeline_presets.py`**), **site_projects** (**`is_archived`**, **`started_at`/`completed_at`**, **`log_events`** JSONB — журнал выполнения проекта; ранее колонка **`logs`**, переименование миграцией **`t7u8v9w0x1yb`**, см. **`docs/CURRENT_STATUS.md`**, **19.04.2026 — Этап 1**; **`serp_config`**, **`project_keywords`** JSONB — миграции **`e7f8a9b0c1d2`**, **`f1a2b3c4d5e7`**, **`g2b3c4d5e6f8`**, **`j4k5l6m7n8oa`**; **`use_site_template`** boolean default true — миграция **`r4s5t6u7v8wd`**: при **`false`** пайплайн не подставляет HTML-шаблон сайта в переменные и не оборачивает **`full_page_html`**, см. **`docs/CURRENT_STATUS.md`**; **`competitor_urls`** JSONB NOT NULL default **`[]`** — миграция **`v0a1b2c3d4e5`**, ручные URL конкурентов для мержа с SERP в **`phase_serp`**, см. **`docs/CURRENT_STATUS.md`**, **«21 апреля 2026 — task41»**), project_content_anchors; одноразовая нормализация **`language`** (**`INITCAP(TRIM)`**) на **`authors`** и **`sites`**: миграция **`s6t7u8v9w0xe`**. Таблица **`site_templates`** удалена миграцией **`i3d4e5f6a7b8`** (данные перенесены в **`templates`** + связь на **`sites`**).

## Фоновые задачи

**Celery** (v5.3.6+)
- Worker: выполнение pipeline задач; конкретный список фаз берётся из **`_pipeline_plan`** (пресет и optional custom-шаги страницы блупринта — см. **`pipeline_presets.py`**)
- Beat: периодический cleanup stale tasks (каждые 10 минут)
- `task_acks_late=True` — задачи не теряются при падении worker
- `task_time_limit=1800` + `task_soft_time_limit=1500` (per-page task)
- **`app/config.py`:** **`STALE_TASK_TIMEOUT_MINUTES`** (по умолчанию 15), **`STEP_TIMEOUT_MINUTES`** (по умолчанию **30** после **task52**) — бюджет «running»-шага в Beat и в **`runner._run_phase`**; **`PIPELINE_STEP_TIMEOUT_SECONDS`** выровнен под 30 мин (**1800**)
- Проекты выполняются по модели page-per-task: `process_site_project` (starter) → `advance_project` (coordinator) → `process_project_page` (isolated page run)
- **Логирование воркера (апрель 2026, 19.04):** при старте процесса воркера — **`configure_logging`** в **`worker_process_init`** (**`app/workers/celery_app.py`**), файл **`logs/worker.log`**; вокруг **`run_pipeline`** — **`structlog.contextvars`** (**`task_id`**, **`project_id`**) в **`app/workers/tasks.py`** — см. **`docs/CURRENT_STATUS.md`**, **«19 апреля 2026 — Этап 1»**
- **Force-delete (апрель 2026, 19.04):** при принудительном удалении проекта или сайта API вызывает **`celery_app.control.revoke(site_projects.celery_task_id, terminate=True)`** (ошибки revoke логируются, удаление в БД продолжается) — **`app/api/projects.py`**, **`app/api/sites.py`**, см. **`docs/CURRENT_STATUS.md`**
- **Stale / force-fail и generation task (апрель 2026, task52):** у **`tasks`** хранится **`celery_task_id`**; Beat **`cleanup_stale_tasks`** и **`POST /api/tasks/{id}/force-status`** (**`action=fail`**) вызывают **`revoke(..., terminate=True, signal="SIGTERM")`** по сохранённому id; постановка **`process_generation_task`** через **`app/services/queueing.enqueue_task_generation`**; при старте воркера id дублируется из **`self.request.id`** (**`process_generation_task`**, **`process_project_page`**) — см. **`docs/CURRENT_STATUS.md`**, раздел **«task52»**

**Redis** (7-alpine)
- Брокер сообщений для Celery
- Backend для хранения результатов Celery
- Docker image: redis:7-alpine
- Также используется как кэш-слой для SERP/scraping (TTL-based)

## LLM

**OpenRouter API**
- Единый API к множеству моделей (GPT-5, Claude Sonnet 4.5, Gemini 2.5 Pro, etc.)
- Обёртка через OpenAI Python SDK (`openai>=1.12.0`) в **`app/services/llm.py`** (`generate_text`)
- base_url: `https://openrouter.ai/api/v1`
- Опционально в **`app/config.py`:** `SELF_CHECK_MAX_RETRIES`, `SELF_CHECK_MAX_COST_PER_STEP` — лимиты ретраев самопроверки (exclude-слова, recovery `html_structure`)
- Таймаут HTTP одного completion: дефолт **`LLM_REQUEST_TIMEOUT=600`** с; опционально **`LLM_MODEL_TIMEOUTS`** (строка `model=seconds,...`) — **`timeout_for_model()`** в **`app/services/llm.py`**; per-call таймаут в **`chat.completions.create`**; клиент **`OpenAI(..., timeout=LLM_REQUEST_TIMEOUT)`** — верхняя граница соединения
- Ретраи внутри **`generate_text`**: **`max_retries=2`**; backoff для 502/504/timeout: **5 с**, **10 с** (rate-limit по-прежнему 60/120/180 с)
- **task54 (24.04.2026):** отдельная ветка для **OpenRouter 402** — если в ошибке есть `can only afford N`, `max_tokens` адаптивно снижается и запрос повторяется без sleep; если кейс неразрешим, кидается **`InsufficientCreditsError`** (fail-fast, без бессмысленных повторов)
- **task55 (24.04.2026):** exclude-words retry больше не дублируется в upstream-шагах (`primary_generation*`, `improver`, `primary_generation_legal`) и остаётся только в `final_editing` (через `call_agent_with_exclude_validation` + финальный `remove_violations`)
- OpenRouter fallback routing: при **`LLM_MODEL_FALLBACKS`** вида **`primary=fb1|fb2`** в запрос добавляется **`extra_body={"models": [primary, fb1, fb2]}`** (дедуп primary в хвосте)
- Параметр **`max_tokens`**: из записи промпта (**`prompts.max_tokens`**) передаётся в Chat Completions, если в БД задано **положительное** значение; **`NULL`** или отсутствие параметра — дефолт модели на стороне OpenRouter
- Sampling: **`temperature`** в запросе всегда; **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** добавляются в **`chat.completions.create`** только если заданы (через **`llm_sampling_kwargs_from_prompt`** при **`_*_enabled`** — см. **`docs/CURRENT_STATUS.md`**, **8.04.2026**)
- Cost / usage: разбор сырого тела ответа (**`usage.cost`**, токены, **`prompt_tokens_details.cached_tokens`**, **`completion_tokens_details.reasoning_tokens`**), фолбэк **`x-openrouter-cost`**, затем оценка по токенам (см. **`docs/CURRENT_STATUS.md`**, **`app/services/llm.py`**)

**Модели по умолчанию:**
- `DEFAULT_MODEL`: openai/gpt-5 (генерация, редактура)
- `ANALYST_MODEL`: google/gemini-2.5-pro (анализ структуры)
- `CLUSTERING_MODEL`: openai/gpt-4o (кластеризация доп. ключей проекта по страницам blueprint, см. `app/services/keyword_clusterer.py`)
- Каждый агент может использовать свою модель и лимит токенов вывода (настраиваются в промптах в UI / БД)

## Image Generation (optional)
- GoAPI.ai (Midjourney proxy) для генерации изображений из Midjourney промптов
- ImgBB как хостинг для размещения финальных картинок
- Опциональная цепочка шагов в pipeline: `image_prompt_generation` (LLM, генерация по каждому MULTIMEDIA-блоку) → `image_generation` (GoAPI + upload) → пауза ревью → `image_inject` (вставка в HTML)
- Настройки: `IMAGE_GEN_ENABLED`, `GOAPI_API_KEY`/`GOAPI_BASE_URL`, `IMGBB_API_KEY`, `IMAGE_POLL_INTERVAL`, `IMAGE_POLL_TIMEOUT`
- Для фактической генерации нужны одновременно: `IMAGE_GEN_ENABLED=true`, валидный `GOAPI_API_KEY` и валидный `IMGBB_API_KEY`

## SERP & Scraping

**DataForSEO** (основной SERP-провайдер)
- Endpoint: `/v3/serp/google/organic/live/advanced`
- Богатый парсинг: organic, PAA, featured snippets, knowledge graph, AI overview, answer box

**SerpAPI** (fallback для SERP)
- Автоматическое переключение при ошибке DataForSEO
- Endpoint: `/search` (engine=google)

**Serper.dev** (основной скрапер)
- Webcrawler API для извлечения HTML страниц конкурентов
- Fallback на direct HTTP если ключ невалиден
- Per-URL кэш в Redis (`scrape_cache:*`) с TTL (`SCRAPE_CACHE_TTL`)

**BeautifulSoup4** (v4.12.3+)
- Парсинг HTML: извлечение h1-h6, body text, word count
- Также извлечение `meta_title` (`<title>`) и `meta_description` (`<meta name="description">`, fallback `og:description`) для SERP URL review
- Удаление script/style/nav/footer перед извлечением текста

**Requests** (v2.31.0+)
- HTTP-клиент для всех внешних API
- ThreadPoolExecutor для параллельного скрапинга (до 10 потоков)

**SERP cache настройки**
- `SERP_CACHE_ENABLED` — kill-switch кэш-слоя
- `SERP_CACHE_TTL` — TTL для агрегированного SERP (`serp_cache:*`)
- `SCRAPE_CACHE_TTL` — TTL для per-URL scraping cache (`scrape_cache:*`)

**Health-check SERP (операционный)**
- **`GET /api/health/serp`** — провайдеры DataForSEO / SerpAPI, агрегат **`overall`**, кэш ответа **5 минут**, query **`force=true`** для принудительной проверки (`app/api/health.py`, `app/services/serp.py`: `get_serp_health`)

## Админ-панель

**React SPA (Vite)**
- React Router v6; основные бизнес-страницы + `/templates` (HTML Templates), `/sites`, `/legal-pages`, `/prompts` (SEO Workflow Optimizer)
- Работает на порту 3000 (в Docker)
- **Локальная сборка и `tsc`:** требуется **Node.js 18+** (Vite/TypeScript 5 не поддерживают Node 12/14)
- Общается с backend через REST API (http://web:8000/api)
- Tailwind CSS & shadcn/ui для стилей
- TanStack Query для стейт-менеджмента и кеширования
- Страница **Prompts**: сохранение через **`PUT /api/prompts/{id}`** с полями **`_*_enabled`**; гидратация формы через **`syncedPromptIdRef`** (см. **`docs/CURRENT_STATUS.md`**, апрель 2026); **`ModelSelector`** — портал в **`document.body`** (`createPortal` + `position: fixed`), см. также **3.04.2026**; **Top P** при **`top_p_enabled=false`** в UI — **`0`** (визуально), сохранение **`top_p: 0`** — см. **`CURRENT_STATUS.md`**, **11.04.2026**; Variable Explorer — переменные legal (**`legal_reference`**, **`page_type_label`**, …, **21.04.2026**)
- Страница **Legal Page Templates** (`/legal-pages`): формат контента **text/html**, при **text** — **textarea** для тела образца, при **html** — Monaco (**`LegalPagesPage`**, **21.04.2026**, см. **`CURRENT_STATUS.md`**)
- Axios response interceptor: ошибки API в **`toast.error`** только как строка (**`formatApiErrorDetail`** в `frontend/src/lib/apiErrorMessage.ts`) — в т.ч. для **`detail`** в виде массива объектов валидации FastAPI; опционально **`skipErrorToast`** на запросе; **`RouteErrorBoundary`** вокруг маршрутов в `App.tsx`
- Проекты: REST-фильтры **`GET /api/projects`**, **`POST /api/projects/preview`** (в т.ч. **`use_site_template`**, эффективный **`has_template`**, предупреждение в **`warnings`** при отключённой обёртке; **20.04.2026** — без **`target_site`** в preview: режим markup-only, см. **`CURRENT_STATUS.md`**), **`POST /api/projects/cluster-keywords`**, **`POST /api/projects/delete-selected`** (массовое удаление, опционально **`force`**, **19.04.2026**), **`GET .../export-csv`**, **`GET .../export-docx`**, clone/start, агрегаты cost/timing/log_events, **`serp_config`**, **`project_keywords`**, **`use_site_template`**, **`competitor_urls`** (**21.04.2026 — task41**, create/clone/list/detail); **`POST /api/projects`** — опциональный **`target_site`** (**`SiteProjectCreate`**) и **`MARKUP_ONLY_SITE_KEY`** / **`_resolve_site_or_markup_only`** в **`app/api/projects.py`** при создании без сайта (**20.04.2026**, см. **`CURRENT_STATUS.md`**); **`legal_template_map`** и автоподстановка из **`GET /legal-pages/for-blueprint/{id}`** (**`default_template_id`**, **18.04.2026**); **`DELETE /api/projects/{id}?force`**, **`POST /api/projects/{id}/reset-status`** (**19.04.2026**); одиночный DOCX: **`GET /api/articles/{id}/download?format=docx`**, **`GET /api/tasks/{id}/export-docx`**; правка HTML статьи — **`PATCH /api/articles/{id}`**; правка **`result`** завершённого шага задачи — **`PUT /api/tasks/{id}/step-result`** — см. **`docs/CURRENT_STATUS.md`** (март–апрель 2026)
- **Sites / язык (18.04.2026):** **`GET /api/sites`** и **`GET /api/sites/{id}`** отдают **`template_id`**, **`template_name`**, **`has_template`**; при создании проекта UI может дергать деталку сайта; нормализация **`language`** на записи (**`authors`**, **`sites`**) и миграция **`s6t7u8v9w0xe`**; фронт **`frontend/src/lib/languageDisplay.ts`** — см. **`CURRENT_STATUS.md`**
- **Authors / task40 (20.04.2026):** **`GET/POST/PUT /api/authors`** — поле **`country_full`**; форма **AuthorsPage** — ввод полного названия страны; см. **`CURRENT_STATUS.md`**, **«20 апреля 2026 — task40»**
- Для SERP URL review: lightweight endpoint **`POST /api/tasks/fetch-url-meta`** (парсинг title/description/domain для одного URL), UI вызывает его при ручном добавлении URL и по кнопке refresh строки
- **Monaco Editor** (**`@monaco-editor/react`**): промпты (**`PromptsPage`** / **`CodeEditor`**), вкладка **Article Review** (**`TaskDetailPage`**, режим Source), вкладка **html** (**`ArticleDetailPage`**, read-only / edit)
- **Force status:** **`POST /api/tasks/{id}/force-status`** — принудительный **`complete`** / **`fail`** для **`processing`** и **`stale`** (см. **`CURRENT_STATUS.md`**, 8.04.2026)

## Уведомления

**Telegram Bot API**
- Уведомления: task success, task failed, serper key issue
- Конфигурация: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
- Тихий fail — не ломает pipeline при ошибке отправки

## Контейнеризация

**Docker** + **docker-compose** (v3.8)
- 5 сервисов: web, worker, beat, redis, frontend (React/Vite, порт **3000**)
- Health checks для web, worker, redis
- Volumes: для **web / worker / beat** в типичном compose смонтирован **`.:/app`** — исполняется **код с хоста**; пересборка образа не подменяет Python без обновления файлов на диске. Сервис **frontend** статику собирает **в образе** — после смены React/TS нужны **`docker compose build --no-cache frontend`** и **`docker compose up -d --force-recreate frontend`** (только **`--build`** иногда оставляет старые слои кэша Docker); затем жёсткое обновление страницы или инкогнито (кэш **`index.html`**).
- Проверка содержимого образа: **`docker compose exec frontend sh -c 'grep -l "Use site HTML template" /app/dist/assets/*.js'`**; ленивые страницы — отдельные чанки (**`ProjectsPage-*.js`** и т.д.).
- Одна команда для запуска: `docker-compose up -d`

## Деплой

**Локальная разработка:**
- `docker-compose up -d` — всё поднимается локально
- Backend: localhost:8000, Frontend (Docker): по умолчанию **localhost:3001** (порт хоста задаётся **`FRONTEND_HOST_PORT`**, см. `docker-compose.yml`; значение по умолчанию **3001**, чтобы не конфликтовать с процессом на **3000**). Локальный `npm run dev` в `frontend/` обычно на другом порту (см. Vite).
- Supabase остаётся облачным

**Production:**
- Backend (FastAPI + Celery + Redis): VPS (DigitalOcean/Hetzner, Ubuntu)
- Frontend (React SPA): Nginx container на том же VPS или статика на Vercel
- Nginx reverse proxy + SSL
- CORS: бэкенд разрешает только домен фронтенда

## Инструменты разработки

**Cursor / Claude** — AI-ассистированная разработка
**GitHub** — контроль версий
**Alembic** — миграции БД; операционный чеклист и **Troubleshooting** (локи, **`idle in transaction`**, разделение DDL/data) — **`.agent/workflows/alembic-migration.md`**
**Swagger UI** (/docs) — тестирование API

---

### Команды для установки и запуска

```bash
# Клонирование и настройка
git clone <repo-url>
cp .env.example .env
# Заполнить .env реальными ключами

# Запуск всей системы
docker-compose up -d --build

# Применение миграций
docker-compose exec web alembic upgrade head

# Проверка статуса
docker-compose ps
docker-compose logs worker -f

# Остановка
docker-compose down