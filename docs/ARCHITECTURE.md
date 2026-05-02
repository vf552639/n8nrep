# ТЕХНИЧЕСКОЕ ЗАДАНИЕ: Миграция фронтенда на React + Полная архитектура проекта

**Проект:** SEO Content Generator  
**Версия ТЗ:** 2.0  
**Дата:** Апрель 2026 (актуализация: **26.04 — task59** — **`app/database.py`**: **`SessionLocal(..., expire_on_commit=False)`**, **`pool_recycle`** из **`DB_POOL_RECYCLE_SECONDS`** (default 60), TCP **keepalives** в **`connect_args`**; **`app/services/pipeline/llm_client.py`**: **`_safe_db`** для **`add_log`**/**`commit`** в progress-колбэках LLM, **`rollback`** перед **`LLMError`**/**`InsufficientCreditsError`**; **`app/services/pipeline/runner.py`**: **`rollback`** перед retry-**`add_log`**; **`app/workers/tasks.py`**: **`rollback`** в **`except`** после **`run_pipeline`**; **`tests/services/test_llm_client_callback_db.py`** — см. **`CURRENT_STATUS.md`**, **«task59»**, коммит **`0b46eb5`**; **23.04 — task53 E** — **`app/database.py`** **`statement_timeout=600000`** мс; **`app/workers/tasks.py`** **`process_project_page`**: полный traceback в **`Task.error_log`**, лог **FAILED** с **`task_id`**, при **`OperationalError`/`DBAPIError`** — **`rollback`**, **`pending`**, **`advance_project.apply_async(..., countdown=60)`**; коммит **`e441738`** — см. **`CURRENT_STATUS.md`**, **«task53 E»**; **22.04 — task52** — **`tasks.celery_task_id`**, миграция **`x9y8z7w6v5u4`**, **`app/services/queueing.py`** (`enqueue_task_generation`, revoke), **`pipeline/runner.py`** (`ThreadPoolExecutor` + **`StepTimeoutError`**, **`step_deadline`**), **`app/services/llm.py`** (**`LLM_REQUEST_TIMEOUT`**, **`LLM_MODEL_TIMEOUTS`**, **`LLM_MODEL_FALLBACKS`**, **`max_retries=2`**), **`llm_client`** (лог fallback-модели, бюджет exclude-retry), **`cleanup_stale_tasks`** / **`POST /tasks/{id}/force-status`** revoke — см. **`CURRENT_STATUS.md`**, раздел **«task52»**; **21.04 — task41** — **`site_projects.competitor_urls`**, **`app/services/url_utils.py`**, мерж в **`phase_serp`**, миграция **`v0a1b2c3d4e5`**, UI **ProjectsPage** / **ProjectDetailPage** — см. **`CURRENT_STATUS.md`**, **«21 апреля 2026 — task41»**; **20.04 — task40** — **`ensure_head_meta`**, **`render_author_footer`**, **`authors.country_full`**, миграция **`u8v9w0x1y2zc`**, **`tests/services/test_template_engine.py`** — см. **`CURRENT_STATUS.md`**, **«20 апреля 2026 — task40»**; **22.04** — **`app/api/tasks.py`**: только **`app/schemas/task`**, **`log_events`** в детали/rerun, **`tests/api/test_routers_happy_path.py`**, CI **`alembic upgrade head`** — см. **`CURRENT_STATUS.md`**, **«22 апреля 2026 — Этап 1: доводка»**; **19.04** — **Этап 1 / task36**: **`app/schemas/`**, **`app/logging_config.py`**, миграция **`t7u8v9w0x1yb`** (**`log_events`**), **`.github/workflows/ci.yml`**, **`README.md`**, **`tests/conftest.py`** — см. **`CURRENT_STATUS.md`**, **«19 апреля 2026 — Этап 1»**; **`app/services/html_export.py`**: **`resolve_export_body`**, **`clean_html_for_paste`**, **`GET /api/tasks/{id}/export-html`**, **`GET /api/projects/{id}/export-html`**, **`docx_builder`** на общем **`resolve_export_body`**; фронт **`TaskDetailPage`** / **`ProjectDetailPage`**; см. **`CURRENT_STATUS.md`**; **21.04** — **`app/services/legal_reference.py`**: **`PAGE_TYPE_LABELS`**, **`page_type_label`**, **`legal_reference`** / **`legal_reference_html`**, **`legal_reference_format`**, **`legal_template_notes`**; **`pipeline_constants`**: **`CRITICAL_VARS`**, **`CRITICAL_VARS_ALLOW_EMPTY`**; seed **`primary_generation_legal`** в **`PROMPTS_FORCE_UPDATE`**; фронт **`LegalPagesPage`** / **`PromptsPage`**; см. **`CURRENT_STATUS.md`**; **20.04** — **`app/api/projects.py`**: **`MARKUP_ONLY_SITE_KEY`**, **`_resolve_site_or_markup_only`**, опциональный **`target_site`** в **`SiteProjectCreate`** / **`ProjectPreviewRequest`**, нормализация **`target_site`** в **`SiteProjectCloneBody`**, create/preview/clone; UI **`ProjectsPage`** — чекбокс **Markup only**; см. **`CURRENT_STATUS.md`**; **19.04** — **`DELETE /{id}?force`**, **`POST /delete-selected`** (**`force`**), **`POST /{id}/reset-status`**, **`_revoke_project_celery_task`**; **`app/api/sites.py`**: **`DELETE /{site_id}?force`**, **409** **`detail.projects[]`**, каскадное удаление проектов/задач; фронт **`ProjectsPage`** / **`ProjectDetailPage`** / **`SitesPage`** — см. **`CURRENT_STATUS.md`**; **18.04** — **`GET /api/sites`**: **`has_template`**, **`_site_out`**, форма проекта (чекбокс **Use site HTML template** при **`site_id`**, **`disabled`** без шаблона) + **`tests/test_sites_api.py`**; **Docker** фронта: **`build --no-cache frontend`**, порт хоста **`3001`**; нормализация **`language`**: миграция **`s6t7u8v9w0xe`**, **`app/utils/language_normalize.py`**, **`languageDisplay.ts`**, **ProjectsPage**/**TasksPage**/**SitesPage**, **`tests/test_language_normalize.py`**; **`site_projects.use_site_template`**, миграция **`r4s5t6u7v8wd`**, **`setup_template_vars`**, **`generate_full_page(..., project_id)`**, **`site_builder`**, API/фронт проектов; **`blueprint_pages.default_legal_template_id`**, **`GET /legal-pages/for-blueprint`**, **`inject_legal_template_vars`**, миграция **`p2q3r4s5t6ub`**; **`legal_page_templates`** без **`title`** (**`q3r4s5t6u7vc`**, API/фронт **`legal_pages`**); **16.04** — **`app/main.py`**: JSON **500** для необработанных исключений, **`lifespan`** + **`verify_migrations()`**; **`app/database.py`**: пул **`pool_pre_ping` / `pool_recycle` / `statement_timeout=600000` мс (task53 E)** в **`connect_args`**, **`get_db`** с **`rollback`** при ошибке; **`alembic/env.py`**: **`SET statement_timeout` / `lock_timeout`** перед онлайн-миграциями; **`.agent/workflows/alembic-migration.md`**: Troubleshooting; **13.04** — пауза **SERP URL review** (**`paused`**, **`_pipeline_pause.reason = serp_review`**, **`GET/POST /tasks/{id}/serp-urls`**, **`SerpUrlsReviewer`**, **`PipelineContext.auto_mode`**, миграция **`m9n0o1p2q3re`**); **11.04** — **`meta_parser`**, **`json_parser.clean_and_parse_json(unwrap_keys)`**, **`meta_generation`**, Top P в Prompts UI; **8.04** — sampling в **`generate_text`**, **`force-status`** для **`stale`**; **Pipeline Presets** per **`blueprint_pages`** — **`pipeline_presets.py`**, динамический **`pipeline.py`**; Monaco HTML на **TaskDetailPage** / **ArticleDetailPage**; **`PUT /tasks/{id}/step-result`**; **`llm.py`** сырой **`usage`**; DOCX **H1** + **Title**; Templates, Legal, keywords, **`meta_generation`**, **Prompts `PUT` / `_*_enabled` / ModelSelector**, см. `CURRENT_STATUS.md`)  
**Для:** antigravity (реализация через Cursor AI)  

**Актуализация (01.05.2026):** на **`blueprint_pages`** добавлено **`hide_author_geo`** (миграция **`y1z2a3b4c5d6`**, commit **`f4ff8d8`**): при финальной сборке статьи **`pipeline/assembly.finalize_article`** в **`render_author_footer(author, hide_geo=...)`** пробрасывается значение из **`ctx.blueprint_page`** (если страницы блупринта нет — полный футер как в task40). См. **`docs/CURRENT_STATUS.md`**, **«Май 2026 — Blueprint: per-page `hide_author_geo`»**.

**Актуализация (май 2026 — task51):** **`GET /api/authors/`** — лёгкий список по умолчанию (**`full=1`** для полного JSON), **`limit`/`offset`**, кэш **60 с**; фронт — React Query **`authorsLightListQueryOptions`** / **`authorsFullListQueryOptions`**; **`PipelineContext`** при инициализации подгружает **`ctx.author`**, далее **`template_vars`** и **`assembly._apply_author_footer`** не делают повторных **`SELECT`**. См. **`docs/CURRENT_STATUS.md`**, **«Май 2026 — task51»**, план **`task51.md`**.

---

## 0. КОНТЕКСТ: Что уже есть

Проект — это рабочая система для массовой SEO-генерации текстов через LLM. Бэкенд полностью готов:

| Компонент | Технология | Статус |
|-----------|-----------|--------|
| Backend API | FastAPI (Python 3.12) | ✅ Готов, работает |
| БД | Supabase (PostgreSQL) + SQLAlchemy/Alembic | ✅ Готова, 10+ таблиц |
| Фоновые задачи | Celery + Redis | ✅ Работает |
| LLM-обёртка | OpenRouter API (GPT-5, Gemini 2.5 Pro, Claude) | ✅ Работает |
| SERP | DataForSEO + SerpAPI (fallback) | ✅ Работает |
| Парсинг | Serper.dev + BeautifulSoup4 (fallback) | ✅ Работает |
| Контейнеризация | Docker + docker-compose | ✅ Работает |
| Текущий UI | React SPA (Vite, Tailwind, TanStack Query) | ✅ Готов, работает |
| Уведомления | Telegram Bot | ✅ Работает |

**Текущий фронтенд на React** — полностью функциональный SPA с real-time обновлениями, продвинутым роутингом и богатым UX.

---

## 1. ПОЛНАЯ СТРУКТУРА ФАЙЛОВ И ПАПОК

```
seo-content-generator/
│
├── docker-compose.yml              # Оркестрация всех сервисов (+ опционально db-test, профиль test)
├── Dockerfile                      # Python backend image
├── .env.example                    # Шаблон переменных окружения
├── pyproject.toml                  # ruff, pytest, mypy (апрель 2026, task36)
├── requirements.txt                # Python зависимости
├── requirements-dev.txt            # Dev/CI зависимости (task36)
├── README.md                       # Запуск тестов, миграции
├── .github/workflows/ci.yml        # CI: backend pytest + ruff (scoped), frontend build
├── alembic.ini                     # Конфигурация Alembic
├── alembic/                        # Миграции БД
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                   # Файлы миграций (уже ~10 штук)
│
├── app/                            # ===== BACKEND (FastAPI) =====
│   ├── main.py                     # Точка входа FastAPI, роутеры, lifespan (verify_migrations), глобальный exception handler → JSON 500, configure_logging
│   ├── config.py                   # Pydantic Settings — загрузка .env (+ LOG_JSON, LOG_LEVEL)
│   ├── logging_config.py           # structlog + stdlib logging (task36)
│   ├── database.py                 # SQLAlchemy engine, SessionLocal (expire_on_commit=False, pool_recycle, keepalives), Base
│   │
│   ├── schemas/                    # Pydantic request/response + JSONB-контракты (task36)
│   │   ├── __init__.py
│   │   ├── task.py, project.py, site.py, author.py, article.py, template.py, legal_page.py, blueprint.py, prompt.py, settings.py
│   │   ├── serp_config.py, step_result.py, log_event.py, jsonb_adapter.py, project_keywords.py
│   │   └── ...
│   │
│   ├── utils/                      # Мелкие утилиты
│   │   └── language_normalize.py   # normalize_language() — единый стиль language при записи (согласовано с INITCAP в миграции s6t7u8v9w0xe)
│   │
│   ├── models/                     # ORM-модели (SQLAlchemy)
│   │   ├── __init__.py             # Re-export всех моделей
│   │   ├── task.py                 # Task — главная таблица заданий (log_events JSONB, celery_task_id task52)
│   │   ├── article.py              # GeneratedArticle — готовые статьи
│   │   ├── site.py                 # Site (template_id → templates, legal_info JSONB)
│   │   ├── template.py            # Template, LegalPageTemplate
│   │   ├── author.py               # Author — виртуальные авторы (+ country_full, task40)
│   │   ├── prompt.py               # Prompt — промпты для LLM-агентов
│   │   ├── blueprint.py            # SiteBlueprint + BlueprintPage (+ default_legal_template_id → legal_page_templates; hide_author_geo — футер автора)
│   │   ├── project.py              # SiteProject — проекты (log_events JSONB, competitor_urls JSONB task41)
│   │   └── project_content_anchor.py # Якоря для дедупликации
│   │
│   ├── api/                        # REST API роутеры
│   │   ├── deps.py                 # Зависимости (API Key auth)
│   │   ├── tasks.py                # /api/tasks — CRUD + bulk + retry + rerun-step + PUT step-result + serp-urls / approve-serp-urls + export-docx + export-html; enqueue через queueing.enqueue_task_generation; force-status fail → revoke (схемы в app/schemas)
│   │   ├── articles.py             # /api/articles — список, просмотр, download html|docx
│   │   ├── sites.py                # /api/sites — CRUD сайтов (_site_out: template_id, template_name, has_template, legal_info; PATCH; DELETE ?force; 409 + projects[]; normalize language on write)
│   │   ├── templates.py            # /api/templates — CRUD глобальных HTML-шаблонов
│   │   ├── legal_pages.py          # /api/legal-pages — CRUD + for-blueprint (default_template_id per page_type)
│   │   ├── authors.py              # /api/authors — CRUD авторов (normalize language; country_full в list/create/update)
│   │   ├── prompts.py              # /api/prompts — GET/POST/PUT + тестирование промптов
│   │   ├── blueprints.py           # /api/blueprints — CRUD блупринтов и страниц (+ default_legal_template_id, hide_author_geo, валидация)
│   │   ├── projects.py             # /api/projects — CRUD + preview/clone/start + cluster-keywords + delete-selected + export-csv/export-docx/export-html + stop/resume + approve-page; competitor_urls (task41); optional target_site (markup-only → __markup_only__); DELETE ?force; POST {id}/reset-status
│   │   ├── dashboard.py            # /api/dashboard — статистика и очередь
│   │   ├── settings_api.py         # /api/settings — чтение/запись .env
│   │   └── health.py               # /api/health — проверка worker'ов
│   │
│   ├── services/                   # Бизнес-логика
│   │   ├── queueing.py             # enqueue_task_generation, revoke_generation_celery_task (task52)
│   │   ├── serp.py                 # DataForSEO + SerpAPI fallback
│   │   ├── serp_cache.py           # Redis TTL cache for SERP/scraping
│   │   ├── scraper.py              # HTTP scraping + BeautifulSoup
│   │   ├── llm.py                  # OpenRouter wrapper + retry; timeout_for_model, fallbacks_for_model, extra_body.models (task52)
│   │   ├── prompt_llm_kwargs.py    # Сборка temperature/max_tokens/… из Prompt + флагов *_enabled
│   │   ├── pipeline/               # Пакет pipeline: runner.py (оркестрация, ThreadPoolExecutor step-timeout task52), context.py (step_deadline), assembly.py, llm_client.py, persistence.py, vars.py, template_vars.py, steps/* (реестр шагов)
│   │   ├── pipeline_presets.py     # Пресеты full/category/about/legal/custom, resolve_pipeline_steps, use_serp
│   │   ├── pipeline_constants.py   # Константы шагов + критические переменные
│   │   ├── template_engine.py      # generate_full_page; ensure_head_meta; render_author_footer(author, hide_geo=…); при use_site_template=false — без обёртки
│   │   ├── legal_reference.py      # inject_legal_template_vars: project.legal_template_map → BlueprintPage default → пусто
│   │   ├── site_builder.py         # Сборка ZIP: full_page_html или fallback html_content; warning при пустом full_page_html (task40)
│   │   ├── notifier.py             # Telegram уведомления
│   │   ├── deduplication.py        # Дедупликация контента в проектах
│   │   ├── exclude_words_validator.py # Валидация запрещённых слов
│   │   ├── json_parser.py          # clean_and_parse_json(text, unwrap_keys?) — LLM JSON; unwrap только для ai_structure
│   │   ├── meta_parser.py          # extract_meta_from_parsed, meta_variant_list — title/description/H1 из meta_generation (+ DOCX)
│   │   ├── url_utils.py            # normalize_url, merge_urls_dedup_by_domain — competitor URLs проекта + SERP (task41)
│   │   ├── word_counter.py         # Подсчёт слов видимого текста (HTML → текст)
│   │   ├── html_inserter.py        # programmatic_html_insert — вставка HTML в шаблон без LLM (fallback html_structure)
│   │   ├── image_utils.py          # MULTIMEDIA из outline: мультиязычные ключи, строка/list, текстовые паттерны
│   │   ├── image_generator.py      # GoAPI (Midjourney proxy) генератор
│   │   ├── image_hosting.py        # ImgBB uploader
│   │   ├── keyword_clusterer.py    # LLM-кластеризация доп. ключей проекта по страницам blueprint
│   │   ├── docx_builder.py         # DOCX: проект целиком + одиночная статья/задача (build_project_docx, build_single_article_docx, build_task_export_docx)
│   │   └── html_export.py          # HTML для MODX: resolve_export_body, clean_html_for_paste, build_project_html_zip/concat; общий приоритет тела с docx_builder
│   │
│   └── workers/                    # Celery
│       ├── celery_app.py           # Конфигурация Celery + Beat schedule; worker_process_init → configure_logging
│       └── tasks.py                # Celery: process_generation_task, process_site_project(starter), advance_project, process_project_page
│
├── frontend/                       # ===== FRONTEND (React) =====
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── Dockerfile                  # Отдельный Docker для фронтенда
│   │
│   ├── public/
│   │   └── favicon.svg
│   │
│   └── src/
│       ├── main.tsx                # Точка входа React
│       ├── App.tsx                 # Главный компонент с роутингом
│       ├── vite-env.d.ts
│       │
│       ├── api/                    # Слой работы с API
│       │   ├── client.ts           # Axios instance с baseURL и API key
│       │   ├── tasks.ts            # Функции для /api/tasks/*
│       │   ├── articles.ts         # Функции для /api/articles/*
│       │   ├── sites.ts            # Функции для /api/sites/*
│       │   ├── templates.ts        # /api/templates/*
│       │   ├── legalPages.ts       # /api/legal-pages/*
│       │   ├── authors.ts          # Функции для /api/authors/*
│       │   ├── prompts.ts          # /api/prompts/* (в т.ч. updateInPlace → PUT)
│       │   ├── blueprints.ts       # Функции для /api/blueprints/*
│       │   ├── projects.ts         # /api/projects/* (в т.ч. deleteSelected, deleteProject force, resetProjectStatus; SiteProjectCreatePayload.target_site optional)
│       │   ├── dashboard.ts        # Функции для /api/dashboard/*
│       │   └── settings.ts         # Функции для /api/settings/*
│       │
│       ├── types/                  # TypeScript типы
│       │   ├── task.ts             # Task, TaskCreate, TaskStep и т.д.
│       │   ├── article.ts          # Article, FactCheckIssue
│       │   ├── site.ts             # Site (template_id, legal_info)
│       │   ├── template.ts         # HtmlTemplate, LegalPageTemplate*
│       │   ├── author.ts           # Author
│       │   ├── prompt.ts           # Prompt, PromptTest
│       │   ├── blueprint.ts        # Blueprint, BlueprintPage
│       │   ├── project.ts          # Project, ProjectTask (log_events)
│       │   └── common.ts           # Общие типы (ApiResponse, PaginatedList)
│       │
│       ├── hooks/                  # Кастомные React хуки
│       │   ├── usePolling.ts       # Автообновление данных по таймеру
│       │   ├── useApi.ts           # Generic хук для API-вызовов с loading/error
│       │   └── useToast.ts         # Уведомления в UI
│       │
│       ├── components/             # Переиспользуемые компоненты
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx     # Навигация + сворачивание (иконки/текст, localStorage)
│       │   │   ├── Header.tsx      # Шапка с breadcrumbs
│       │   │   └── MainLayout.tsx  # Обёртка: Sidebar + Header + content
│       │   │
│       │   ├── common/
│       │   │   ├── StatusBadge.tsx  # Цветной бейдж статуса (pending/processing/...)
│       │   │   ├── DataTable.tsx    # Универсальная таблица с пагинацией и фильтрами
│       │   │   ├── ConfirmDialog.tsx # Модалка подтверждения действия
│       │   │   ├── CodeEditor.tsx   # Monaco Editor для промптов
│       │   │   ├── JsonViewer.tsx   # Красивый рендеринг JSON (SERP, outline)
│       │   │   ├── CopyButton.tsx   # Кнопка копирования в буфер
│       │   │   └── LoadingSpinner.tsx
│       │   │
│       │   ├── tasks/
│       │   │   ├── TaskCreateForm.tsx      # Форма создания задачи
│       │   │   ├── TaskBulkImport.tsx      # Загрузка CSV
│       │   │   ├── StepMonitor.tsx         # Мониторинг шагов pipeline (ГЛАВНЫЙ)
│       │   │   ├── StepCard.tsx            # Карточка шага + вложенные вьюхи
│       │   │   ├── steps/                  # SerpStepView, ScrapingStepView, LlmStepView, parseStepResult
│       │   │   ├── StepRerunForm.tsx       # Форма перегенерации шага
│       │   │   ├── SerpViewer.tsx          # Рендеринг SERP-данных
│       │   │   ├── SerpUrlsReviewer.tsx    # Пауза serp_review: правка списка URL перед scraping
│       │   │   ├── ImageReviewPanel.tsx    # Пауза image_review после image_generation
│       │   │   └── QueueControls.tsx       # Кнопки «Следующая», «Запустить все»
│       │   │
│       │   ├── articles/
│       │   │   ├── ArticlePreview.tsx      # Iframe-превью статьи
│       │   │   ├── ArticleSourceCode.tsx   # HTML-код с подсветкой
│       │   │   ├── FactCheckPanel.tsx      # Панель факт-чекинга
│       │   │   └── ArticleMetrics.tsx      # Метрики (word count, etc.)
│       │   │
│       │   ├── ModelSelector.tsx           # Селектор модели OpenRouter (портал + fixed)
│       │   ├── ToggleSwitch.tsx          # iOS-стиль переключатель (Model Settings)
│       │   │
│       │   ├── projects/
│       │   │   ├── ProjectCreateForm.tsx   # Форма создания проекта
│       │   │   ├── ProjectProgress.tsx     # Прогресс-бар проекта
│       │   │   └── ProjectTaskList.tsx     # Список задач проекта
│       │   │
│       │   └── dashboard/
│       │       ├── StatsCards.tsx          # Карточки метрик
│       │       ├── CeleryStatus.tsx        # Статус воркеров
│       │       └── RecentTasks.tsx         # Последние задачи
│       │
│       ├── pages/                  # Страницы (вкладки UI)
│       │   ├── DashboardPage.tsx   # 📊 Дашборд
│       │   ├── TasksPage.tsx       # ✅ Задачи
│       │   ├── TaskDetailPage.tsx  # Детали задачи + StepMonitor; логи из API: log_events
│       │   ├── ArticlesPage.tsx    # 📝 Статьи
│       │   ├── ArticleDetailPage.tsx # Детали статьи + превью
│       │   ├── TemplatesPage.tsx   # HTML Templates (/templates)
│       │   ├── SitesPage.tsx       # Сайты (/sites)
│       │   ├── LegalPagesPage.tsx  # Legal page templates (/legal-pages)
│       │   ├── AuthorsPage.tsx     # 👥 Авторы
│       │   ├── PromptsPage.tsx     # 🤖 Промпты (SEO Workflow Optimizer, /prompts)
│       │   ├── BlueprintsPage.tsx  # 🏗️ Блупринты
│       │   ├── ProjectsPage.tsx    # 📁 Проекты
│       │   ├── ProjectDetailPage.tsx # Детали проекта + задачи
│       │   ├── LogsPage.tsx        # 📜 Логи
│       │   └── SettingsPage.tsx    # ⚙️ Настройки
│       │
│       └── styles/
│           └── globals.css         # Tailwind base + кастомные стили
│
├── tests/                          # Тесты Python (апрель 2026: conftest, factories, api/, маркер integration)
│   ├── conftest.py                 # Postgres + Alembic при TEST_DATABASE_URL; db_session + api_db_session с rollback; async_api_client
│   ├── factories.py                # factory_boy: Site, Task, Author, Project, Blueprint, BlueprintPage, Prompt, Template, LegalPageTemplate, Article
│   ├── api/
│   │   ├── conftest.py             # autouse-моки LLM/SERP/scraper, eager Celery, привязка к api_db_session (task37)
│   │   ├── test_app_routes.py      # Smoke GET по всем роутерам FastAPI
│   │   ├── test_routers_crud.py    # CRUD/404/422 для tasks/projects/templates (taskco)
│   │   ├── test_tasks_api.py       # per-router: tasks (task37)
│   │   ├── test_projects_api.py    # per-router: projects + competitor_urls (task37/task41)
│   │   ├── test_templates_api.py   # per-router: templates (task37)
│   │   ├── test_authors_api.py     # per-router: authors + country_full (task37/task40)
│   │   ├── test_sites_api.py       # per-router: sites (task37)
│   │   ├── test_articles_api.py    # per-router: articles (task37)
│   │   ├── test_blueprints_api.py  # per-router: blueprints (task37)
│   │   ├── test_prompts_api.py     # per-router: prompts (task37)
│   │   ├── test_settings_api.py    # per-router: settings (task37)
│   │   ├── test_legal_pages_api.py # per-router: legal pages (task37)
│   │   ├── test_logs_api.py        # per-router: logs (task37)
│   │   ├── test_dashboard_api.py   # per-router: dashboard (task37)
│   │   └── test_health_api.py      # per-router: health (task37)
│   ├── services/
│   │   ├── test_pipeline_smoke.py  # @pytest.mark.integration; test_run_pipeline_minimal_happy_path (taskco); test_phase_serp_merges_project_competitor_urls (task41)
│   │   └── test_template_engine.py # ensure_head_meta, render_author_footer (task40; hide_geo — май 2026)
│   ├── workers/
│   │   ├── test_tasks_unit.py      # Юниты воркера без БД
│   │   └── test_process_generation_task_integration.py  # Celery eager mode, мок LLM, валидация LogEvent (taskco)
│   ├── unit/
│   │   └── test_url_utils.py       # normalize_url, merge_urls_dedup_by_domain (task41)
│   ├── test_logging_config.py      # structlog / configure_logging
│   ├── test_api.py
│   ├── test_html_export.py
│   ├── test_html_inserter.py
│   ├── test_image_utils.py
│   ├── test_json_parser.py
│   ├── test_language_normalize.py
│   ├── test_legal_reference_inject.py
│   ├── test_meta_parser.py
│   ├── test_prompt_llm_kwargs.py
│   └── test_sites_api.py
│
└── data/
    └── exports/                    # Папка для ZIP-архивов проектов
```

---

## 2. ОПИСАНИЕ КАЖДОГО КОМПОНЕНТА И ЕГО ФУНКЦИЙ

### 2.1 Backend (app/) — УЖЕ ГОТОВ, НЕ ТРОГАЕМ

#### app/services/pipeline/runner.py + app/services/pipeline/steps/* — Ядро системы
Сейчас runtime пайплайна модульный: **порядок шагов** для конкретной задачи строится из **`resolve_pipeline_steps`** (`pipeline_presets.py`) по странице блупринта (`pipeline_preset`, optional `pipeline_steps_custom`), затем `runner.py` проходит по `_pipeline_plan.steps` и вызывает step-классы из `STEP_REGISTRY` (`pipeline/steps/*`). Ниже — полный «классический» набор шагов (подмножество может выполняться для `about` / `legal` / `category` и т.д.):

1. **SERP Research** → `serp_research` — запрос к DataForSEO/SerpAPI
2. **Competitor Scraping** → `competitor_scraping` — парсинг ТОП-10 конкурентов
3. **AI Structure Analysis** → `ai_structure_analysis` — анализ интентов/таксономии (Gemini)
4. **Chunk Cluster Analysis** → `chunk_cluster_analysis` — LSI-ключи, семантические кластеры
5. **Competitor Structure Analysis** → `competitor_structure_analysis` — паттерны конкурентов
6. **Final Structure Analysis** → `final_structure_analysis` — финальный план (JSON)
7. **Structure Fact-Checking** → `structure_fact_checking` — проверка плана
8. **Primary Generation** → `primary_generation` — генерация текста (GPT-5)
8b. **Primary Generation About / Legal** → `primary_generation_about` / `primary_generation_legal`
9. **Competitor Comparison** → `competitor_comparison` — сравнение с конкурентами
10. **Reader Opinion** → `reader_opinion` — оценка от читателя
11. **Interlinking & Citations** → `interlinking_citations` — перелинковка
12. **Improver** → `improver` — доработка по фидбэку
13. **Final Editing** → `final_editing` — финальная редактура (**`editing_context`** пустой; HTML через **`{{result_improver}}`**, outline через **`{{result_final_structure_analysis}}`** в промпте из БД; без дублирования в **`[CONTEXT]`** и без строк «target word count» / «current article stats» — см. **`docs/CURRENT_STATUS.md`**, **`final_editing`**)
14. **Content Fact-Checking** → `content_fact_checking` — факт-чекинг
15. **HTML Structure** → `html_structure` — форматирование HTML (LLM + при сильной потере контента recovery и при необходимости **`programmatic_html_insert`** из `html_inserter.py`)
16. **Meta Generation** → `meta_generation` — JSON (часто **`{"results": [{Title, Description, H1, Trigger}, …]}`**); при сборке статьи **`title`/`description`** в **`GeneratedArticle`** берутся из **первого варианта**, полный JSON пишется в **`meta_data`**

**Сборка `GeneratedArticle.full_page_html` (task40, 20.04; доп. май 2026):** после **`generate_full_page(...)`** результат (шаблон или «сырой» HTML) всегда прогоняется через **`ensure_head_meta`** из **`template_engine`** с **`title`/`description`** из **`extract_meta_from_parsed`**; затем в конец документа добавляется **`render_author_footer(author, hide_geo=...)`** (перед первым **`</body>`**): при **`ctx.blueprint_page.hide_author_geo`** скрываются строки «Страна» / «Код страны» / «Город». См. **`docs/CURRENT_STATUS.md`**, **«20 апреля 2026 — task40»** и **«Май 2026 — Blueprint: per-page `hide_author_geo`»**.

Опционально для image-цепочки (между структурами и генерацией текста):
- `phase_image_prompt_gen()` — извлечение `MULTIMEDIA` блоков через `image_utils.extract_multimedia_blocks` (мультиязычные ключи, строка/list, паттерны в тексте; при пустом результате — fallback по сырому outline) и генерация промпта по каждому блоку (переменные `type`, `description`, `purpose`, `parent_title`, `location`)
- `phase_image_gen()` — генерация через GoAPI + загрузка в ImgBB
- `phase_image_inject()` — вставка одобренных изображений в HTML

**Примечание про DOCX:** `docx_step` в runtime-пайплайне не используется по дизайну. DOCX формируется post-factum через `app/services/docx_builder.py` и export-endpoints (`/api/tasks/{id}/export-docx`, `/api/articles/{id}/download?format=docx`, `/api/projects/{id}/export-docx`).

Каждый шаг:
- Проверяет `step_results[step_key]` — если `completed`, пропускает (resume)
- Загружает промпт из БД (`get_prompt_obj`)
- Подставляет переменные (`apply_template_vars`) — `{{keyword}}`, `{{language}}` и т.д.
- Вызывает LLM через `generate_text` (с retry); kwargs sampling собираются в **`call_agent`** через **`llm_sampling_kwargs_from_prompt()`** (`app/services/prompt_llm_kwargs.py`): **`temperature`** всегда (**0.7** при выключенном **`temperature_enabled`**); **`frequency_penalty`**, **`presence_penalty`**, **`top_p`**, **`max_tokens`** попадают в словарь (и далее в HTTP-запрос) только при соответствующем **`_*_enabled`** и валидном значении — отключённые ключи **не** передаются в OpenRouter (см. **`docs/CURRENT_STATUS.md`**, **8.04.2026**). В лог задачи пишется строка **`LLM params`** (**`format_llm_params_log_line`**) с **(custom|default)** для temperature и только для фактически переданных полей.
- Сохраняет результат + стоимость + resolved prompts в `step_results`

#### app/services/llm.py — LLM-обёртка
- Единая точка вызова OpenRouter API (`generate_text`)
- **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** — опциональные аргументы (**`None`** = не добавлять ключ в тело запроса)
- Опционально **`max_tokens`**: если передан не-`None` и **> 0**, уходит в `chat.completions`; иначе провайдер использует дефолт модели
- Retry с экспоненциальным backoff (429 → 60/120/180s, 502/504 → 15/30/45s)
- Возвращает `(text, cost, actual_model, usage_or_none)` — приоритет стоимости: **`usage.cost`** из сырого JSON ответа, иначе заголовок **`x-openrouter-cost`**, иначе оценка по токенам; в **`usage`** при наличии в ответе: **`cached_tokens`**, **`reasoning_tokens`**
- В **`call_agent`** лог **`response_received`** дополняется **`⚡ N cached`** / **`🧠 R reasoning`** (см. `docs/CURRENT_STATUS.md`, раздел про **`llm.py`**)
- Используется через `call_agent()` и `call_agent_with_exclude_validation()`, а также эндпоинтами теста промптов

#### app/services/serp.py — SERP-данные
- **DataForSEO** (основной) → парсит organic, PAA, related, featured snippet, knowledge graph, AI overview, answer box
- **SerpAPI** (fallback) → аналогичный парсинг
- Возвращает унифицированную структуру с urls, organic_results, paa_full, serp_features и т.д.
- Финальный SERP-результат оборачивается Redis-кэшем (`serp_cache:*`) с TTL; в summary шага передаётся `_from_cache`.

#### app/services/scraper.py — Парсинг конкурентов
- Serper.dev webcrawler (основной) → прямой HTTP (fallback)
- Параллельный scraping через ThreadPoolExecutor
- Извлечение h1-h6 + body text через BeautifulSoup
- Фильтрация excluded domains (соцсети, отзовики)
- Per-URL Redis-кэш (`scrape_cache:*`) с метриками `cache_hits` / `cache_misses` в результате шага.

#### app/workers/ — Celery задачи
- `process_generation_task` — обёртка для pipeline (одна задача)
- `process_site_project` — стартер проекта (инициализация и запуск координатора)
- `advance_project` — координатор: выбор следующей страницы / финализация проекта
- `process_project_page` — изолированная обработка одной страницы (one page = one Celery task)
- `cleanup_stale_tasks` — Celery Beat: каждые 10 минут чистит зависшие задачи и проверяет step-level timeouts

### 2.2 Frontend (frontend/) — УЖЕ ГОТОВ

#### Технологии для фронтенда:

| Что | Технология | Почему |
|-----|-----------|--------|
| Framework | React 18 + TypeScript | Типобезопасность, экосистема |
| Сборка | Vite | Быстрый dev-сервер, ESBuild |
| Стили | Tailwind CSS | Быстрая вёрстка, утилитарный подход |
| UI-библиотека | shadcn/ui | Красивые компоненты, не тяжёлая зависимость |
| Таблицы | TanStack Table (React Table v8) | Сортировка, фильтры, пагинация |
| HTTP | Axios | Interceptors для API key, error handling |
| Роутинг | React Router v6 | Стандарт |
| Код-редактор | Monaco Editor (@monaco-editor/react) | Подсветка промптов |
| Графики | Recharts | Для дашборда — легковесные графики |
| Иконки | Lucide React | Консистентные иконки |
| Уведомления | react-hot-toast | Тосты для успехов/ошибок |
| State | React Query (TanStack Query) | Кеширование API-ответов, автообновление |

### 2.3 Детальное описание каждой страницы фронтенда

#### DashboardPage.tsx
**Endpoint'ы:** `GET /api/dashboard/stats` (в т.ч. **`cost_by_day`** — суммы **`total_cost`** по дням за ~30 дней для completed-задач), `GET /api/dashboard/queue`, `GET /api/health/serp`

Что показывает:
- 5 метрик-карточек: Total / Processing / Completed / Failed / Pending
- Статус Celery workers (online/offline)
- Количество сайтов
- Столбчатый график (Recharts) по **`cost_by_day`**, если есть данные
- Последние 10 задач (из `GET /api/tasks?limit=10&skip=0` → поле **`items`**)

#### TasksPage.tsx + TaskDetailPage.tsx
**Endpoint'ы:** `GET /api/tasks` (ответ **`{ items, total }`**; query: **`skip`**, **`limit`**, **`status`**, **`search`**, **`site_id`**), `POST /api/tasks`, `POST /api/tasks/bulk`, `POST /api/tasks/next`, `POST /api/tasks/start-all`, **`POST /api/tasks/start-selected`**, `GET /api/tasks/{id}`, `GET /api/tasks/{id}/steps`, **`PUT /api/tasks/{id}/step-result`** (ручное обновление **`result`** завершённого шага + **`_prev_versions`**), **`GET /api/tasks/{id}/export-docx`**, **`GET /api/tasks/{id}/export-html`**, `GET /api/tasks/{id}/serp-data`, `GET /api/tasks/{id}/serp-export`, `POST /api/tasks/{id}/retry`, `POST /api/tasks/{id}/approve`, `POST /api/tasks/{id}/rerun-step`, `POST /api/tasks/{id}/force-status`, `DELETE /api/tasks/{id}`, `GET /api/tasks/{id}/images`, `POST /api/tasks/{id}/approve-images`

**TasksPage:**
- Таблица задач с фильтрами по статусу и сайту, **серверной** пагинацией (напр. 50 строк на страницу), поиском по ключу на бэкенде
- Первая колонка: чекбоксы для **`pending`** задач, **Select all** в заголовке, кнопка **Start Selected (N)** → `POST /api/tasks/start-selected`
- Форма создания задачи (keyword, country, language, site, author, page_type)
- Массовый импорт CSV
- Кнопки управления очередью (Следующая / Запустить все) — в sequential mode

**TaskDetailPage** (отдельная страница по клику):
- Основные табы: **Pipeline Execution** и **Execution Logs**; дополнительно могут появляться `Image Review` и `Article Review` по состоянию задачи.
- **Article Review:** **Preview** (iframe) + **Source** (**Monaco**, HTML); выбор источника — последний завершённый шаг из цепочки к черновику/HTML (в т.ч. **`primary_generation*`**); **Edit** / **Save** → **`PUT /api/tasks/{id}/step-result`** (**`tasksApi.updateStepResult`**).
- **StepMonitor** + **StepCard** для шагов из **`_pipeline_plan.steps`** (или упорядоченно по **`step_results`**):
  - `serp_research` / `competitor_scraping` — специализированные вьюхи (`SerpStepView`, `ScrapingStepView`): метрики, таблицы, ссылка на SERP ZIP для SERP.
  - Остальные шаги — **LlmStepView**: табы Result / Prompts / Variables, `ExcludeWordsAlert` при нарушениях.
- Логи в UI: поля **`ts`**, **`msg`**, **`level`**, **`step`** (как пишет `add_log` в pipeline).
- Кнопка перегенерации шага с feedback
- Force Complete / Force Fail для задач в статусе **`processing`** или **`stale`** (**`POST /api/tasks/{id}/force-status`**)
- **Export DOCX** (при **`completed`**, готовом **`final_editing`** или черновиках **`primary_generation_about` / `primary_generation_legal`**) — **`GET /api/tasks/{id}/export-docx`** через **`tasksApi.exportDocx`**; **Download / Copy HTML** при **`completed`** — **`GET /api/tasks/{id}/export-html`** (**`tasksApi.exportHtml`**, **`exportHtmlDownload`**)

#### ArticlesPage.tsx + ArticleDetailPage.tsx
**Endpoint'ы:** `GET /api/articles`, `GET /api/articles/{id}` (в т.ч. **`full_page_html`**, **`fact_check_issues`**), **`PATCH /api/articles/{id}`** (правка **`html_content`**, опционально title/description; пересчёт **`word_count`**), `GET /api/articles/{id}/preview`, **`GET /api/articles/{id}/download`** (query **`format`**: не задан / **`html`** → HTML, **`docx`** → Word), `POST /api/articles/{id}/issues/{idx}/resolve`

**ArticlesPage:**
- Таблица: title, word_count, fact_check_status, needs_review, created_at

**ArticleDetailPage:**
- Meta Title + Description (вкладка metadata / **`meta_data`**)
- Факт-чекинг панель (issues с severity, кнопка «Пометить исправлено») — данные из **`fact_check_issues`**
- Вкладка **html**: один **Monaco** (**read-only** / **редактирование** по кнопке **Edit HTML**) + **Save** через **`PATCH /api/articles/{id}`** (без дублирования `<pre>` + отдельного редактора)
- Iframe-превью
- Скачивание **.html** и **.docx** через blob (axios + API key; **`articlesApi.downloadBlob(id, "html" | "docx")`**), не «голая» ссылка

#### PromptsPage.tsx (`/prompts`, заголовок UI: «SEO Workflow Optimizer»)

**Endpoint'ы:** `GET /api/prompts`, `GET /api/prompts/{id}` (в т.ч. **`max_tokens`**, все **`_*_enabled`**), **`PUT /api/prompts/{id}`** (in-place: тексты, модель, числа и **пять булевых `_*_enabled`**), `POST /api/prompts/` (новая версия агента), `POST /api/prompts/test`, `POST /api/prompts/{id}/test` (тело: **`context`**, опционально overrides модели и sampling — см. **`PromptTestContext`**), `GET /api/prompts/{id}/versions`, `POST /api/prompts/{id}/versions/{source_prompt_id}/restore`, `GET /api/settings/openrouter-models`. При сохранении тексты проходят **`_sanitize()`** — см. `app/api/prompts.py`.

**Layout:** колонка **Available Agents** | центр: **Model Settings** (градиентная панель, **`ModelSelector`**, **`ToggleSwitch`** + слайдеры **`model-slider`**, **`Save`** `blue-600`) + **Test**, **Skip in pipeline**, **Monaco** (System, User) | **Variable Explorer**. **`ModelSelector`:** портал в **`document.body`**, **`position: fixed`**. Гидратация **`editState`** и **`paramsEnabled`**: **`useRef` `syncedPromptIdRef`** — при первом появлении ответа для данного **`fullPrompt.id`** выполняется полная синхронизация с сервера; при refetch с тем же id локальные правки не сбрасываются. Зависимости эффекта: **`[derivedActiveId, fullPrompt?.id]`**. На этом маршруте `MainLayout` скрывает глобальный `Header`.

**Поведение:** **`paramsEnabledFromPrompt`** читает только серверные **`_*_enabled`**; **`isPromptDirty`** учитывает все пять тогглов и значения при включённых параметрах; **`saveMutation`** → **`updateInPlace`** с флагами; **`PromptTestPanel`** получает **`llm: PromptTestLlmOptions`** (несохранённые параметры попадают в тест). См. **`docs/CURRENT_STATUS.md`**, раздел **«Model Settings: флаги *_enabled»**.

#### ProjectsPage.tsx + ProjectDetailPage.tsx
**Endpoint'ы:** `POST /api/projects/preview` (dry-run; **`use_site_template`**, эффективный **`has_template`**, **`site.use_site_template`** в ответе), `POST /api/projects/cluster-keywords` (preview распределения ключей), `GET /api/projects` (query: **`archived`**, **`status`**, **`search`**; в элементе: **`progress`**, **`total_cost`**, **`is_archived`**, **`use_site_template`**, GEO, счётчики задач), `POST /api/projects` (**`SiteProjectCreate`**, **`target_site`**, **`serp_config`**, опц. **`project_keywords`**, **`use_site_template`**, опц. **`serp_warning`** в ответе), `GET /api/projects/{id}` (деталка + **`total_cost`**, **`started_at`/`generation_started_at`/`completed_at`**, **`log_events`**, **`serp_config`**, **`project_keywords`**, **`use_site_template`**), `POST .../{id}/clone` (опц. **`use_site_template`**), `POST .../{id}/start`, `GET .../{id}/export-csv`, `GET .../{id}/export-docx` (DOCX, требуется ≥1 `completed` task), `GET .../{id}/export-html` (ZIP или concat, те же условия), `POST .../archive`, `POST .../unarchive`, `DELETE .../{id}` (не при `generating`/`pending`), `POST .../retry-failed`, `POST .../stop`, `POST .../resume`, `POST .../approve-page`, `GET .../download`; дубликат проекта — **409** + **`existing_project_id`**

**ProjectsPage:**
- Таблица: **Active / Archived**, фильтр статуса, поиск по имени; колонки **Progress**, **Pages** (completed/total), **Failed**, **Country/Lang**; **Archive** / **Restore** в последней колонке (**`stopPropagation`** от клика по строке)
- Модалка **New Project**: **`target_site`**, **Preview**, опционально **Additional Keywords** + **Cluster Keywords** (preview), Advanced **SERP**; деталка: **Clone**, **Start**, **Export CSV**, **Export DOCX** (при наличии completed-страниц), cost/timing/log_events; toasts через **`formatApiErrorDetail`** (**409** с **`existing_project_id`**); **`projectsApi.create`** с **`skipErrorToast`**

**ProjectDetailPage:**
- Прогресс-бар, **failed_count**, GEO в шапке
- **Retry Failed Pages** (если есть failed-задачи и проект не в `generating`/`pending`), **Retry page** у отдельной задачи со статусом **`failed`** (**`POST /api/tasks/{id}/retry`**), **Delete** (confirm; не в `generating`/`pending`), Stop / Resume, **Export DOCX** (если `completed_tasks > 0`), Download ZIP
- Блоки ошибок: красный при **`failed`**, янтарный при **`completed`** + **`error_log`** (частичные сбои страниц)
- Список задач с StepMonitor, **`StepMonitor`** для статуса **`processing`**

#### BlueprintsPage.tsx
**Endpoint'ы:** `GET /api/blueprints`, `POST /api/blueprints`, `GET /api/blueprints/{id}/pages`, `POST /api/blueprints/{id}/pages`, `PUT /api/blueprints/{id}/pages/{page_id}`, `DELETE /api/blueprints/{id}/pages/{page_id}`

- Таблица блупринтов с **раскрывающейся строкой**; под ней панель **Pages** (lazy-загрузка страниц), таблица полей страницы, Add/Edit/Delete, **Keyword Preview**; после **Create Blueprint** новая строка раскрывается автоматически
- CRUD блупринтов
- Таблица страниц: page_slug, page_title, page_type, keyword_template, keyword_template_brand, filename, sort_order, use_serp, **pipeline_preset**, optional **pipeline_steps_custom** (custom-чекбоксы шагов в UI), show_in_nav, show_in_footer, **hide_author_geo** (чекбокс в Add/Edit: скрыть страну/код/город автора в HTML-футере); колонка **Pipeline** в таблице

#### TemplatesPage.tsx (`/templates`)
**Endpoint'ы:** `GET/POST /api/templates`, `GET/PUT/DELETE /api/templates/{id}`

- Список глобальных HTML-шаблонов: имя, число сайтов, active, Preview / Edit / Delete
- Модалка **Add template**: Template Name, Description, HTML (Monaco), Active — без привязки к сайту

#### LegalPagesPage.tsx (`/legal-pages`)
**Endpoint'ы:** `GET /api/legal-pages?country=`, `GET /api/legal-pages/meta/page-types`, `GET/POST/PUT/DELETE /api/legal-pages/{id}`

- Таблица образцов legal-страниц по GEO: country, page_type, title, active; фильтр по стране
- Модалка: Country, Page Type (privacy_policy, terms_and_conditions, …), Title, HTML (Monaco), Variables (JSON), Notes

#### SitesPage.tsx (`/sites`)
**Endpoint'ы:** `GET /api/sites`, `POST /api/sites` (опц. **`template_id`**), `GET /api/sites/{id}`, `PATCH /api/sites/{id}`, `DELETE /api/sites/{id}` (при наличии задач с `target_site_id` или проектов с `site_id` — **409**)

- Список сайтов с колонкой **Template**; модалка **Add Site**: Country/Language из **`GET /api/authors`**, опционально выбор **`template_id`** из **`GET /api/templates`**

#### SiteDetailPage.tsx (`/sites/:id`)
**Endpoint'ы:** `GET /api/sites/{id}`, `PATCH /api/sites/{id}`; для блока шаблонов — **`GET/POST/PUT/DELETE /api/templates`** (глобальные шаблоны, не вложенные в `/sites/...`).

- Форма сайта: **name, domain, country, language, is_active**, выбор **`template_id`**, JSON **`legal_info`**
- Блок **глобальных HTML-шаблонов**: Add / Edit (Monaco) / Delete, ссылка на **`/templates`**

#### AuthorsPage.tsx
**Endpoint'ы:** `GET /api/authors`, `POST /api/authors`, `DELETE /api/authors/{id}`

- Таблица авторов
- Форма: author, country, language, bio, imitation, year, face, target_audience, rhythms_style, exclude_words

#### SettingsPage.tsx
**Endpoint'ы:** `GET /api/settings`, `PUT /api/settings`

- API ключи (OpenRouter, DataForSEO, SerpAPI, Serper, Telegram)
- Системные: Celery concurrency, exclude words, sequential mode

#### LogsPage.tsx
**Endpoint:** `GET /api/tasks/{id}` → `task.log_events` (элементы: `ts`, `msg`, `level`, опционально `step`)

- Выбор задачи → лента логов
- На **TaskDetailPage** вкладка Execution Logs использует тот же формат полей

*Примечание:* глобальная страница Logs может отличаться по фильтрам — см. актуальный код.

---

## 3. СХЕМА ВЗАИМОДЕЙСТВИЯ МЕЖДУ КОМПОНЕНТАМИ

### 3.1 Общая архитектура (runtime)

```
┌──────────────┐     HTTP/REST      ┌──────────────┐
│              │◄──────────────────►│              │
│   React UI   │  JSON + API Key    │  FastAPI      │
│  (Vite)      │                    │  Backend      │
│  :5173/:3000 │                    │  :8000        │
└──────────────┘                    └──────┬───────┘
                                          │
                              ┌───────────┼───────────┐
                              │           │           │
                              ▼           ▼           ▼
                        ┌──────────┐ ┌─────────┐ ┌──────────┐
                        │ Supabase │ │  Redis  │ │ External │
                        │ (Postgres)│ │         │ │  APIs    │
                        │          │ │         │ │          │
                        └──────────┘ └────┬────┘ └──────────┘
                                          │       OpenRouter
                                          │       DataForSEO
                                    ┌─────┴─────┐ SerpAPI
                                    │  Celery   │ Serper.dev
                                    │  Worker   │ Telegram
                                    └───────────┘
```

### 3.2 Поток данных: Создание задачи → Готовая статья

```
React UI                    FastAPI                    Celery Worker
   │                           │                           │
   │  POST /api/tasks          │                           │
   │  {keyword, country, ...}  │                           │
   │──────────────────────────►│                           │
   │                           │  INSERT Task (pending)    │
   │                           │──────────► DB             │
   │                           │                           │
   │                           │  process_generation_task  │
   │                           │  .delay(task_id)          │
   │                           │──────────────────────────►│
   │  {"id": "...", "status":  │                           │
   │   "queued"}               │                           │
   │◄──────────────────────────│                           │
   │                           │                           │
   │  GET /api/tasks/{id}/steps│     run_pipeline()        │
   │  (polling каждые 5-10s)   │                           │
   │──────────────────────────►│     phase_serp()          │
   │  {progress: 12%,          │     phase_scraping()      │
   │   current_step: "serp"}   │     phase_ai_structure()  │
   │◄──────────────────────────│     ...                   │
   │                           │     phase_meta_gen()      │
   │  ...повтор polling...     │                           │
   │                           │     INSERT Article        │
   │  GET /api/tasks/{id}/steps│     Task.status=completed │
   │  {progress: 100%}         │                           │
   │◄──────────────────────────│◄──────────────────────────│
   │                           │     Telegram notification │
   │  GET /api/articles/{id}   │                           │
   │──────────────────────────►│                           │
   │  {title, html_content,    │                           │
   │   word_count, ...}        │                           │
   │◄──────────────────────────│                           │
```

### 3.3 Архитектура Pipeline (детально)

```
                        ┌─────────────────────────────────────┐
                        │         run_pipeline(db, task_id)   │
                        │                                     │
 use_serp=true          │  ┌──────────────────────────┐       │  use_serp=false
 (article, homepage,    │  │ PHASE 1: Research        │       │  (about, privacy,
  category)             │  │ ► SERP Research          │       │   terms, legal)
                        │  │ ► Competitor Scraping    │       │
                        │  └──────────┬───────────────┘       │   Пропускает
                        │             │                       │   фазы 1-3,
                        │  ┌──────────▼───────────────┐       │   идёт сразу
                        │  │ PHASE 2: Analysis        │       │   к Primary Gen
                        │  │ ► AI Structure (Gemini)  │       │
                        │  │ ► Chunk Cluster          │       │
                        │  │ ► Competitor Structure   │       │
                        │  │ ► Final Structure (JSON) │       │
                        │  │ ► Structure Fact-Check   │       │
                        │  └──────────┬───────────────┘       │
                        │             │                       │
                        │  ┌──────────▼───────────────┐       │
                        │  │ PHASE 3: Generation      │◄──────┤
                        │  │ ► Primary Generation     │       │
                        │  └──────────┬───────────────┘       │
                        │             │                       │
                        │  ┌──────────▼───────────────┐       │
                        │  │ PHASE 4: Review (SERP)   │       │
                        │  │ ► Competitor Comparison   │       │
                        │  │ ► Reader Opinion          │       │
                        │  │ ► Interlinking           │       │
                        │  │ ► Improver               │       │
                        │  └──────────┬───────────────┘       │
                        │             │                       │
                        │  ┌──────────▼───────────────┐       │
                        │  │ PHASE 5: Finalization    │       │
                        │  │ ► Final Editing          │       │
                        │  │ ► Content Fact-Check     │       │
                        │  │ ► HTML Structure         │       │
                        │  │ ► Meta Generation        │       │
                        │  └──────────┬───────────────┘       │
                        │             │                       │
                        │  ┌──────────▼───────────────┐       │
                        │  │ SAVE: Article + Template │       │
                        │  │ ► GeneratedArticle       │       │
                        │  │ ► full_page_html         │       │
                        │  │ ► Dedup anchors          │       │
                        │  │ ► Telegram notify        │       │
                        │  └─────────────────────────────────┘
```

### 3.4 Система промптов: от UI до LLM

```
Промпт в БД                     Pipeline                          OpenRouter
┌───────────────┐               ┌──────────────────┐             ┌──────────┐
│ system_prompt │               │ apply_template_  │             │          │
│ "Analyze      │──────────────►│ vars()           │────────────►│ Gemini / │
│ {{keyword}}   │               │                  │             │ GPT-5 /  │
│ for {{lang}}" │               │ {{keyword}} →    │  HTTP POST  │ Claude   │
│               │               │ "best casinos"   │             │          │
│ user_prompt   │               │ {{lang}} → "de"  │             └──────────┘
│ "Context:     │               │                  │
│ {{merged_     │               │ + rerun_feedback │
│   markdown}}" │               │ + exclude_words  │
│               │               │   injection      │
│ model: gemini │               │                  │
│ temp: 0.7     │               │                  │
└───────────────┘               └──────────────────┘
     ▲
     │  Редактирование
     │  из UI (PromptsPage)
```

---

## 4. РЕКОМЕНДАЦИИ ПО ТЕХНОЛОГИЯМ (ДЛЯ НОВИЧКА)

### 4.1 Что уже настроено и НЕ НУЖНО ТРОГАТЬ

- **Не трогай `app/`** — весь бэкенд работает, API задокументирован в Swagger (`/docs`)
- **Не трогай `alembic/`** — миграции управляются отдельно
- **Не трогай `docker-compose.yml`** — добавляй только секцию `frontend`
- **Не трогай `.env`** — только добавь `VITE_API_URL` для фронтенда

### 4.2 Как подключить фронтенд к бэкенду

```typescript
// frontend/src/api/client.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY || '',
  },
});

export default api;
```

### 4.3 Как работает polling для мониторинга задач

Это ключевой UX-паттерн. Когда задача в статусе `processing`, UI должен опрашивать бэкенд каждые 5-10 секунд:

```typescript
// frontend/src/hooks/usePolling.ts
import { useEffect, useRef } from 'react';

export function usePolling(callback: () => void, intervalMs: number, enabled: boolean) {
  const savedCallback = useRef(callback);
  savedCallback.current = callback;

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => savedCallback.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}

// Использование:
const { data, refetch } = useQuery(['task-steps', taskId], () => fetchTaskSteps(taskId));
usePolling(refetch, 8000, data?.status === 'processing');
```

### 4.4 React Query — зачем и как

React Query кеширует API-ответы и управляет состоянием загрузки. Вместо `useState` + `useEffect` + `fetch`:

```typescript
// Вместо ручного fetch:
const { data: tasks, isLoading, error } = useQuery({
  queryKey: ['tasks', { status, page }],
  queryFn: () => api.get('/tasks', { params: { status, skip: page * 50, limit: 50 } }),
});

// Для мутаций (создание, удаление):
const createTask = useMutation({
  mutationFn: (data: TaskCreate) => api.post('/tasks', data),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
});
```

### 4.5 Как добавить фронтенд в docker-compose

```yaml
# Добавить в docker-compose.yml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  ports:
    - "3000:3000"
  environment:
    - VITE_API_URL=http://web:8000/api
  depends_on:
    web:
      condition: service_healthy
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
RUN npm install -g serve
CMD ["serve", "-s", "dist", "-l", "3000"]
```

---

## 5. ПЛАН РЕАЛИЗАЦИИ ПО ЭТАПАМ (Выполнено)

### Этап 1: Инициализация проекта (1 день)

**Задачи:**
1. Создать `frontend/` с Vite + React + TypeScript
2. Настроить Tailwind CSS + shadcn/ui
3. Создать `api/client.ts` с Axios + API key
4. Создать `types/` — все TypeScript интерфейсы по моделям бэкенда
5. Создать `MainLayout.tsx` с Sidebar (навигация по вкладкам)
6. Настроить React Router v6 с lazy loading

**Проверка:** `npm run dev` → видна боковая навигация, роутинг работает, API-вызов к `/api/dashboard/stats` возвращает данные.

### Этап 2: Dashboard + Tasks (2-3 дня)

**Задачи:**
1. `DashboardPage` — метрики + статус Celery
2. `TasksPage` — таблица задач с DataTable (фильтры, пагинация)
3. `TaskCreateForm` — форма создания (с автоподбором автора по стране/языку)
4. `TaskBulkImport` — CSV загрузка
5. `QueueControls` — кнопки «Следующая» / «Запустить все» (sequential mode)
6. `TaskDetailPage` + `StepMonitor` — **САМЫЙ ВАЖНЫЙ КОМПОНЕНТ**:
   - Прогресс-бар
   - Карточки по фактическому плану шагов задачи (пресет страницы блупринта)
   - Для каждого шага: результат (textarea), resolved prompts (code), debug переменные (таблица)
   - Кнопка перегенерации шага (StepRerunForm)
   - SerpViewer для шага serp_research
   - Force Complete / Force Fail
   - Авто-polling при status=processing

**Проверка:** Создать задачу из UI → видеть прогресс в реальном времени → задача завершена → результат доступен.

### Этап 3: Articles + Prompts (2-3 дня)

**Задачи:**
1. `ArticlesPage` — таблица статей
2. `ArticleDetailPage`:
   - Meta Title / Description
   - FactCheckPanel — issues с severity, кнопка resolve
   - ArticleSourceCode — HTML с подсветкой (Monaco Editor, read-only)
   - ArticlePreview — iframe с `src="/api/articles/{id}/preview"`
   - Кнопка скачать
3. `PromptsPage`:
   - Табы по агентам пайплайна (в т.ч. **about** / **legal** primary generation)
   - Monaco Editor для system/user prompt
   - VariableReference — справочник `{{keyword}}` и т.д.
   - ModelSelector — загрузка списка моделей из OpenRouter API
   - Настройки: temperature, freq_penalty, pres_penalty, top_p
   - PromptTestPanel — dry run с показом результата + стоимости

**Проверка:** Просмотреть статью → увидеть HTML-превью → отредактировать промпт → тестировать dry run.

### Этап 4: Projects + Blueprints (2 дня)

**Задачи:**
1. `BlueprintsPage` — CRUD блупринтов + страниц
2. `ProjectsPage` — таблица проектов
3. `ProjectCreateForm`:
   - Выбор блупринта → превью keyword_template с seed подстановкой
   - seed_is_brand checkbox
   - Авто-подбор автора
4. `ProjectDetailPage`:
   - ProjectProgress — прогресс-бар (completed/total)
   - Stop / Resume кнопки
   - ProjectTaskList — задачи проекта с прогрессом
   - Скачать ZIP
   - Встроенный StepMonitor для выбранной задачи

**Проверка:** Создать проект → видеть последовательное выполнение → Stop → Resume → ZIP.

### Этап 5: Sites + Authors + Settings + Logs (1-2 дня)

**Задачи:**
1. `TemplatesPage` — глобальные HTML-шаблоны; `SitesPage` / `SiteDetailPage` — сайты и привязка `template_id`; `LegalPagesPage` — legal templates по GEO
2. `AuthorsPage` — CRUD с полным набором полей
3. `SettingsPage` — API ключи + системные настройки
4. `LogsPage` — выбор задачи → лента логов с фильтрацией

### Этап 6: Полировка + Docker (1 день)

**Задачи:**
1. Responsive design для всех страниц
2. Error boundaries
3. Loading states для всех таблиц/форм
4. Dark mode (опционально — Tailwind поддерживает из коробки)
5. Dockerfile для фронтенда
6. Обновить docker-compose.yml — секция frontend
7. Тест: `docker-compose up -d` → всё работает

---

## 6. КРИТИЧЕСКИЕ НЮАНСЫ ДЛЯ CURSOR AI

### 6.1 Не генерировать бэкенд заново
Бэкенд **полностью готов**. Все API endpoint'ы описаны в Swagger по адресу `/docs`. Cursor должен ТОЛЬКО создавать фронтенд и подключать его к существующему API.

### 6.2 StepMonitor + StepCard — мониторинг pipeline
**StepMonitor** рендерит список шагов в фиксированном порядке (см. `StepMonitor.tsx` / `pipeline_constants`).

**StepCard** (раскрытие шага) содержит детали:
- `serp_research` / `competitor_scraping` — отдельные компоненты (`steps/SerpStepView`, `steps/ScrapingStepView`): метрики, таблицы, ссылка на SERP export.
- Остальные шаги — `steps/LlmStepView`: табы **Result / Prompts / Variables**, `ExcludeWordsAlert` при нарушениях.
- **StepRerunForm** для завершённых шагов; статус/стоимость/duration в шапке карточки.

### 6.3 Список шагов pipeline (из кода)
```typescript
const PIPELINE_STEPS = [
  { key: 'serp_research', label: '🔍 SERP Research' },
  { key: 'competitor_scraping', label: '🕷️ Парсинг конкурентов' },
  { key: 'ai_structure_analysis', label: '🧠 AI анализ структуры' },
  { key: 'chunk_cluster_analysis', label: '📊 Анализ кластера' },
  { key: 'competitor_structure_analysis', label: '🏗️ Анализ конкурентов' },
  { key: 'final_structure_analysis', label: '📐 Финальная структура' },
  { key: 'structure_fact_checking', label: '🔍 Факт-чек структуры' },
  { key: 'primary_generation', label: '✍️ Первичная генерация' },
  { key: 'competitor_comparison', label: '⚖️ Сравнение с конкурентами' },
  { key: 'reader_opinion', label: '👤 Мнение читателя' },
  { key: 'interlinking_citations', label: '🔗 Перелинковка' },
  { key: 'improver', label: '💎 Улучшайзер' },
  { key: 'final_editing', label: '✅ Финальная редактура' },
  { key: 'content_fact_checking', label: '🔍 Факт-чекинг контента' },
  { key: 'html_structure', label: '🏷️ Структура HTML' },
  { key: 'meta_generation', label: '🏷️ Мета-теги' },
];
```

### 6.4 Формат данных от API (примеры)

**GET /api/tasks/{id}/steps:**
```json
{
  "task_id": "uuid",
  "status": "processing",
  "total_cost": 0.0042,
  "progress": 56,
  "current_step": "primary_generation",
  "step_results": {
    "serp_research": {
      "status": "completed",
      "result": "{\"source\": \"dataforseo\", \"urls_count\": 10, ...}",
      "model": null,
      "cost": 0,
      "timestamp": "2026-03-20T12:00:00"
    },
    "primary_generation": {
      "status": "running",
      "result": null,
      "timestamp": "2026-03-20T12:05:00"
    }
  }
}
```

**GET /api/prompts/{id}:**
```json
{
  "id": "uuid",
  "agent_name": "primary_generation",
  "system_prompt": "You are an SEO writer for {{language}} market...",
  "user_prompt": "Write an article about {{keyword}} with {{avg_word_count}} words...",
  "version": 3,
  "is_active": true,
  "skip_in_pipeline": false,
  "model": "openai/gpt-5",
  "max_tokens": 8000,
  "temperature": 0.7,
  "frequency_penalty": 0.3,
  "presence_penalty": 0.1,
  "top_p": 0.95
}
```

### 6.5 Переменные промптов (полный список)

Задача/Автор: `keyword`, `additional_keywords`, `country`, `language`, `page_type`, `competitors_headers`, `merged_markdown`, `avg_word_count`, `author`, `author_style`, `imitation`, `target_audience`, `face`, `year`, `rhythms_style`, `exclude_words`, `site_name`, `site_template_html`, `site_template_name`, `legal_reference`, `legal_reference_html` (алиас), `legal_reference_format`, `legal_template_notes`, `page_type_label`, `legal_variables`, `already_covered_topics` (legal-поля — при **use_serp=false** и типе страницы из набора legal, см. `app/services/legal_reference.py`, **`CURRENT_STATUS.md`** **21.04.2026**)

SERP: `competitor_titles`, `competitor_descriptions`, `highlighted_keywords`, `paa_with_answers`, `featured_snippet`, `knowledge_graph`, `ai_overview`, `answer_box`, `serp_features`, `search_intent_signals`, `related_searches`

Результаты предыдущих шагов: `result_ai_structure_analysis`, `intent`, `Taxonomy`, `Attention`, `structura`, `result_chunk_cluster_analysis`, `result_competitor_structure_analysis`, `result_final_structure_analysis`, `structure_fact_checking`

Проект: `page_slug`, `page_title`, `all_site_pages`

---

## 7. ДОРОЖНАЯ КАРТА ПОСЛЕ ФРОНТЕНДА (из Плана развития)

После создания React UI, следующие приоритеты (реализовать в бэкенде):

1. **Quality Gate** — валидация output'ов LLM после каждого шага (min_output_length, JSON validity, HTML tags)
2. **Fallback-модель** — поле `fallback_model` в Prompt, автопереключение при отказе основной
3. **Target Word Count** — поле в Task, контроль длины статьи
4. **Аналитика стоимости** — breakdown по моделям/шагам в дашборде
5. **Параллельные шаги** — ThreadPoolExecutor для 3 аналитических шагов
6. **Inline-редактор статьи** — PUT /api/articles/{id}
7. **Rate Limiter** — Redis-based для LLM-вызовов
