# ROADMAP

**Последнее обновление:** апрель 2026 (**task55**: exclude-words retry оставлен только в `final_editing`; в `draft_step.py`/`legal_step.py` upstream-шаги переведены на `call_agent` без `call_agent_with_exclude_validation`, что снижает повторные дорогие LLM-вызовы; ранее **task54**, коммит **`08fa216`**: NUL-санитизация scraped/SERP payloads + OpenRouter 402 adaptive `max_tokens` downscale и fail-fast `InsufficientCreditsError`; до этого **task53 E**, **task52**, **task50**)

---

## Q1 2026 (Январь — Март) — MVP ✅

- [x] Инициализация FastAPI проекта, структура папок
- [x] Подключение к Supabase через SQLAlchemy + Alembic миграции
- [x] Настройка Celery + Redis + Docker-compose
- [x] Pipeline генерации контента (базовый «полный» путь; с **апреля 2026** — настраиваемые пресеты per страница блупринта, см. **`CURRENT_STATUS.md`**, **6 апреля 2026**)
- [x] DataForSEO + SerpAPI (fallback) для SERP
- [x] Serper.dev + Direct HTTP (fallback) для скрапинга
- [x] OpenRouter LLM wrapper с retry policy
- [x] React SPA админ-панель (10 разделов)
- [x] Система промптов с версионированием и test dry-run
- [x] **`max_tokens`** из промпта → `generate_text` / pipeline (`call_agent`) и тест-эндпоинты (`/api/prompts/test`, `/api/prompts/{id}/test`); поле в UI **SEO Workflow Optimizer** (см. `CURRENT_STATUS.md`, 28.03.2026)
- [x] Telegram-уведомления
- [x] Массовый импорт задач через CSV
- [x] Система проектов + блупринты + site builder (ZIP)
- [x] Дедупликация контента (ProjectContentAnchor)
- [x] Exclude Words (глобальные + per-author)
- [x] Факт-чекинг контента (soft/strict)
- [x] Rerun отдельных шагов с feedback + каскадная инвалидация
- [x] Test Mode (пауза после primary generation)
- [x] SERP Viewer + CSV/ZIP export
- [x] Страница **Prompts** (`/prompts`): рабочая область «SEO Workflow Optimizer» — агенты, Model Settings, светлые Monaco (vs), Variable Explorer, тест LLM с `resolved_prompts`, версии/restore (`docs/CURRENT_STATUS.md`, раздел март 2026)
- [x] **Tasks / Task Detail:** выборочный запуск (`start-selected`), StepCard с Serp/Scraping/Llm вьюхами, логи по полям `ts`/`msg`, сворачиваемый Sidebar — см. `CURRENT_STATUS.md`
- ~~[x] Маршрут **SEO Setup** (`/seo-setup`)~~ — **удалён** (апрель 2026); настройки покрываются **Settings** + **Sites** + **Templates**
- [x] Stop/Resume проектов
- [x] Force-status для зависших задач
- [x] Cleanup stale tasks (Celery Beat)
- [x] Redis-кэш SERP и per-URL scraping (TTL, kill-switch, инвалидация при rerun)
- [x] Смягчение потери контента на **`html_structure`**: `max_tokens`, recovery, `programmatic_html_insert`, seed Gemini Flash, `SELF_CHECK_*` (см. `docs/CURRENT_STATUS.md`, март–апрель 2026)
- [x] Prompts UI (эволюция до апреля 2026): **Max tokens** / параметры через **`ToggleSwitch`**, панель **Model Settings**, гидратация **`syncedPromptIdRef`** + **`[derivedActiveId, fullPrompt?.id]`**, серверные **`_*_enabled`**, **`isPromptDirty`** по всем тогглам, тест с **`PromptTestLlmOptions`**; санитизация в API + Monaco `unusualLineTerminators: off`; сохранение — **`PUT /api/prompts/{id}`** (ранее hotfix для **`POST`** и нового `id` версии)
- [x] **Sites / Blueprints / Projects (UI):** Add Site и New Project — селекты GEO/язык/автор из авторов; удаление сайта с проверкой зависимостей (**409**); Blueprints — раскрытие строки, панель Pages, после создания блупринта авто-раскрытие (см. `CURRENT_STATUS.md`, раздел «Sites, Blueprints, Projects»)
- [x] **Projects / API / фронт (30.03.2026):** **`POST /api/projects`** — тело с **`target_site`** (маппинг с формы); **`GET /api/projects`** — поле **`progress`**; Axios **`formatApiErrorDetail`** (нет React #31 в toast); **`RouteErrorBoundary`**; см. `CURRENT_STATUS.md`, `Bugs.md` (**BUG-015**)
- [x] **Проекты (конец марта 2026):** архивация (**`is_archived`**, миграция **`e7f8a9b0c1d2`**), фильтры списка, **`DELETE`** / **`retry-failed`**; **skip failed pages** в **`process_site_project`** + аккуратный **`phase_serp`**; UI списка и деталки — см. **`CURRENT_STATUS.md`**, раздел **«30 марта 2026 — Проекты: архивация…»**
- [x] **Проекты (март 2026, расширения):** **`POST /api/projects/preview`**, **`serp_config`** (проект → задачи), **`GET /api/projects/{id}/export-csv`**, **`GET /api/health/serp`**, clone/start, агрегаты cost/timing/**`log_events`**, защита от дубликатов **409**, retry SERP при полном отказе провайдеров, React (Preview, CSV, дашборд SERP) — см. **`CURRENT_STATUS.md`**, раздел **«Проекты: preview…»**
- [x] **Апрель 2026 — Templates + Legal Pages:** глобальная таблица **`templates`**, **`sites.template_id`** и **`sites.legal_info`**, **`legal_page_templates`** по GEO; API **`/api/templates`**, **`/api/legal-pages`**; UI **`/templates`**, **`/sites`**, **`/legal-pages`**; пайплайн: **`legal_reference`** / **`legal_reference_html`**, **`legal_variables`** (актуализация переменных legal — **`CURRENT_STATUS.md`**, **21.04.2026**); миграция **`i3d4e5f6a7b8`** — см. **`CURRENT_STATUS.md`**, **1 апреля 2026**
- [x] **Апрель 2026 — Проекты для контент-менеджеров:** **`GET /api/projects/{id}/export-docx`** (`python-docx`, **`app/services/docx_builder.py`**); **`POST /api/projects/cluster-keywords`** + **`site_projects.project_keywords`** (миграция **`j4k5l6m7n8oa`**); UI: доп. ключи, кластеризация, **Export DOCX**; **`process_project_page`** — слияние кластерных ключей в **`Task.additional_keywords`**
- [x] **Апрель 2026 — Meta generation:** сборка статьи учитывает JSON **`{"results": [...]}`** — `title`/`description` из первого варианта, полный JSON в **`meta_data`**; DOCX-метатаблица с H1 и строками Variant N при нескольких вариантах — см. **`CURRENT_STATUS.md`**, **2 апреля 2026**
- [x] **Апрель 2026 — UI / API (вторая итерация):** удаление Streamlit и сервиса **`frontend`** на 8501; compose-сервис **`frontend`** (React, 3000); **`GET /tasks` → `{ items, total }`**; **`PATCH /articles/{id}`**; **`cost_by_day`** в **`/dashboard/stats`**; **`SiteDetailPage`** (форма сайта + CRUD шаблонов); пагинация **`TasksPage`**; график на дашборде; **`ArticleDetailPage`** edit/download; **`ProjectDetailPage`** retry одной страницы; см. **`CURRENT_STATUS.md`**, **«2 апреля 2026 (вторая итерация)»**
- [x] **Апрель 2026 — DOCX одиночной статьи и задачи:** **`GET /api/articles/{id}/download?format=docx`**, **`GET /api/tasks/{id}/export-docx`**, функции в **`docx_builder.py`**; кнопки **Export DOCX** на **`ArticleDetailPage`** и **`TaskDetailPage`**; **`tasksApi.exportDocx`** — см. **`CURRENT_STATUS.md`**, **«DOCX: одиночная статья и одиночная задача»**; **актуализация:** шапка документа — **H1** из мета, в мета-таблице — строка **Title** (meta title) — раздел **«DOCX одиночной статьи: шапка H1»**
- [x] **Апрель 2026 — LLM / OpenRouter:** **`generate_text`** читает **`usage.cost`** и детали токенов из сырого JSON ответа; логи **`call_agent`** показывают cached/reasoning при наличии — см. **`CURRENT_STATUS.md`**, **«`llm.py`: стоимость и токены из сырого ответа»**
- [x] **Апрель 2026 — Monaco HTML + `step-result`:** **`PUT /api/tasks/{id}/step-result`**, **`tasksApi.updateStepResult`**; **Article Review** на **`TaskDetailPage`** (Monaco Source, бейдж шага-источника); **`ArticleDetailPage`** — единый Monaco на вкладке html — см. **`CURRENT_STATUS.md`**, **«Monaco для HTML: Article Review, Article Detail»**
- [x] **Апрель 2026 — `phase_final_editing`:** **`editing_context`** пустой (статья/outline только в шаблоне промпта); **`setup_template_vars`** дополняет **`result_*`** из **`step_results`**; ранее убраны числовые подсказки по объёму в контексте — см. **`CURRENT_STATUS.md`**, **«final_editing: без дублирования»** / **«Pipeline: контекст шага `final_editing`»**
- [x] **Апрель 2026 — Prompts backend+UI:** **`PUT /api/prompts/{id}`** (in-place), **`ToggleSwitch`**, редизайн Model Settings, портал **`ModelSelector`**, миграция **`k5m6n7o8p9qb`**, **`prompt_llm_kwargs`**, **`syncedPromptIdRef`** — см. **`CURRENT_STATUS.md`** (**«Model Settings: флаги *_enabled»**, **3 апреля 2026**); **`Bugs.md`** (**BUG-013**, **BUG-016**)
- [x] **Апрель 2026 — Pipeline Presets:** колонки **`pipeline_preset`**, **`pipeline_steps_custom`** на **`blueprint_pages`**, сервис **`pipeline_presets.py`**, динамический план в **`pipeline.py`**, UI **Blueprints** + **StepMonitor**, агенты **`primary_generation_about`** / **`primary_generation_legal`**, миграция **`l6m7n8o9p0qc`** — см. **`CURRENT_STATUS.md`**, **6 апреля 2026**
- [x] **Апрель 2026 (8.04):** **`prompt_llm_kwargs`** + **`llm.generate_text`** — без явной передачи **`top_p`/penalties** при **`_*_enabled=false`**; **`POST /tasks/{id}/force-status`** для **`stale`** — см. **`CURRENT_STATUS.md`**, **8 апреля 2026**
- [x] **Апрель 2026 (13.04):** пауза после SERP (**`serp_review`**) для одиночных задач — статус **`paused`**, редактирование **`serp_data.urls`** в UI, **`GET /api/tasks/{id}/serp-urls`**, **`POST /api/tasks/{id}/approve-serp-urls`**, **`PipelineContext.auto_mode`**, без паузы при **`run_pipeline(..., auto_mode=True)`**; **`force-status`** / **`rerun-step`** для **`paused`**; миграция **`m9n0o1p2q3re`** — см. **`CURRENT_STATUS.md`**, **13 апреля 2026**
- [x] **Апрель 2026 (16.04):** защитная инфраструктура — JSON **500**, **`verify_migrations`** в **`lifespan`**, пул **`database.py`** + **`get_db` rollback**, таймауты в **`alembic/env.py`**, Troubleshooting в **`.agent/workflows/alembic-migration.md`** — см. **`CURRENT_STATUS.md`**, **16 апреля 2026**
- [x] **Апрель 2026 (18.04):** двухуровневые legal templates — дефолт **`blueprint_pages.default_legal_template_id`**, override **`site_projects.legal_template_map`**, фолбек в **`inject_legal_template_vars`**, **`GET /legal-pages/for-blueprint`** с **`default_template_id`**, UI **Blueprints** / **Create Project**, миграция **`p2q3r4s5t6ub`**; **`LegalPageTemplate`** без **`title`** (миграция **`q3r4s5t6u7vc`**, UI **Legal Pages**) — см. **`CURRENT_STATUS.md`**, **18 апреля 2026**
- [x] **Апрель 2026 (18.04):** флаг **`site_projects.use_site_template`** — отключение HTML-обёртки сайта для страниц проекта (пайплайн, preview, clone, ZIP); миграция **`r4s5t6u7v8wd`**; UI **New Project** / **Clone project** — см. **`CURRENT_STATUS.md`**, **«Проект: use_site_template»**
- [x] **Апрель 2026 (18.04):** ответ **`GET /api/sites`** — **`has_template`** + **`template_id`** / **`template_name`**; модалка **Create Generative Project**: **`refetchOnMount`**, **`GET /api/sites/{id}`**, **`siteHasTemplate`**; блок чекбокса при **`site_id`**; **`disabled`** и копирайт без шаблона; контрактные тесты **`tests/test_sites_api.py`**; заметки по **Docker** фронта — см. **`CURRENT_STATUS.md`**, **«Sites API и чекбокс Use site HTML template»**
- [x] **Апрель 2026 (18.04):** нормализация **`language`** в БД (**`s6t7u8v9w0xe`**) и при записи авторов/сайтов; фронт **`languageDisplay.ts`** + формы **Projects** / **Tasks** / **Sites**; **`tests/test_language_normalize.py`** — см. **`CURRENT_STATUS.md`**, **«Language: INITCAP и защита на фронте»**
- [x] **Апрель 2026 (19.04):** **HTML-экспорт** — **`app/services/html_export.py`** (**`resolve_export_body`**, **`clean_html_for_paste`**, ZIP/concat проекта), **`GET /api/tasks/{id}/export-html`**, **`GET /api/projects/{id}/export-html`**, рефактор **`docx_builder`** на **`resolve_export_body`**, UI **TaskDetailPage** / **ProjectDetailPage**, **`tests/test_html_export.py`**; зависшие **`pending`**/**`generating`** проекты — **force-delete** (query **`force`**, revoke **`celery_task_id`**), **`POST /projects/delete-selected`**, **`POST /projects/{id}/reset-status`**; **Sites** — **409** / **`force`**; **ProjectsPage**, **ProjectDetailPage**, **SitesPage** — см. **`CURRENT_STATUS.md`**, **«19 апреля 2026»**
- [x] **Апрель 2026 (20.04):** **Markup only** — создание проекта без **Target Site**: опциональный **`target_site`** в **`POST /api/projects`** и **`POST /api/projects/preview`**, резервный сайт **`__markup_only__`**, **`use_site_template=false`**, чекбокс и payload в **`ProjectsPage`** — см. **`CURRENT_STATUS.md`**, **«20 апреля 2026»**
- [x] **Апрель 2026 (20.04, task40):** **`ensure_head_meta`** + **`render_author_footer`** (`template_engine`), сборка **`GeneratedArticle.full_page_html`** в **`pipeline`**, **`authors.country_full`** + миграция **`u8v9w0x1y2zc`**, warning в **`site_builder`**, UI **AuthorsPage**, **`tests/services/test_template_engine.py`** — см. **`CURRENT_STATUS.md`**, **«20 апреля 2026 — task40»**
- [x] **Апрель 2026 (21.04):** legal — промпт **`primary_generation_legal`** и **`inject_legal_template_vars`**: **`legal_reference`** / формат / **`page_type_label`** / **`legal_template_notes`**, **`CRITICAL_VARS`**, **`CRITICAL_VARS_ALLOW_EMPTY`** в **`call_agent`**, обновление seed (**`PROMPTS_FORCE_UPDATE`**), UI **Legal Pages** / **Prompts**, тесты **`test_legal_reference_inject`** — см. **`CURRENT_STATUS.md`**, **«21 апреля 2026 — Legal»**
- [x] **Апрель 2026 (21.04, task41):** **`site_projects.competitor_urls`**, миграция **`v0a1b2c3d4e5`**, **`url_utils`**, мерж в **`phase_serp`**, API/UI проектов, тесты **`tests/unit/test_url_utils.py`**, **`test_phase_serp_merges_project_competitor_urls`**, **`test_create_project_with_competitor_urls`** — см. **`CURRENT_STATUS.md`**, **«21 апреля 2026 — task41»**
- [x] **Апрель 2026 (11.04):** рефакторинг **`clean_and_parse_json`** (**`unwrap_keys`** для **`ai_structure`** только по запросу), устойчивый разбор JSON; модуль **`app/services/meta_parser.py`** (**`extract_meta_from_parsed`**, **`meta_variant_list`**) — унифицированное извлечение title/description/H1 и вариантов для DOCX; сборка статьи в **`pipeline.py`** через **`extract_meta_from_parsed`**, при повторном проходе — **обновление** существующей **`GeneratedArticle`**; **`docx_builder._get_all_meta_from_task`** использует те же функции + **`clean_and_parse_json`** для сырого шага; debug-логи meta; Prompts UI — Top P при выключенном тоггле как **`0`**; тесты **`tests/test_json_parser.py`**, **`tests/test_meta_parser.py`** — см. **`CURRENT_STATUS.md`**, **11 апреля 2026**; **`Bugs.md`** (**BUG-008**)
- [x] **Апрель 2026 (23.04, task53 E):** страницы генеративного проекта — **`statement_timeout`** в **`app/database.py`** поднят до **10 мин**; **`app/workers/tasks.py`** — полный traceback в **`Task.error_log`**, строка **FAILED** в логе проекта с **`task_id`**; при **`OperationalError`/`DBAPIError`** — **`rollback`**, **`pending`**, **`advance_project.apply_async(..., countdown=60)`** без пропуска страницы — см. **`CURRENT_STATUS.md`**, **`task53.md`**, коммит **`e441738`**
- [x] **Апрель 2026 (24.04, task54):** защита от NUL-байтов и 402 по кредитам — `app/utils/text_sanitize.py` (`strip_nul`), санитизация в `scraper.py` и `serp_step.py`; в `llm.py` обработка `402 can only afford N` с downscale `max_tokens` + fail-fast `InsufficientCreditsError`; тесты `tests/unit/test_text_sanitize.py`, `tests/services/test_llm_402_downscale.py`
- [x] **Апрель 2026 (24.04, task55):** exclude-words validation ограничена финальным шагом — в `PrimaryGen*`/`Improver`/`PrimaryGenLegal` убран `call_agent_with_exclude_validation`, оставлен `call_agent`; `final_editing` без изменений (retry + regex-strip), цель — уменьшить стоимость повторных LLM-вызовов

---

## Q2 2026 (Апрель — Июнь) — Стабильность и качество

### Операционная гигиена (апрель 2026) — частично закрыто
- [x] Необработанные исключения API → **`application/json`** с **`detail`** (не **`text/plain`**) — `app/main.py`
- [x] Лог при старте **`web`**, если **`alembic current` ≠ head** — `verify_migrations()` в **`lifespan`**
- [x] Пул SQLAlchemy: **`pool_pre_ping`**, **`pool_recycle`**, лимиты пула, серверный **`statement_timeout`** в **`connect_args`** (**600000** мс после **task53 E**, ранее **60000**); **`get_db`**: **`rollback`** при ошибке — `app/database.py`
- [x] DDL-миграции: **`statement_timeout` / `lock_timeout`** на соединении Alembic — `alembic/env.py`; troubleshooting — **`.agent/workflows/alembic-migration.md`**

### Этап 1 — фундамент качества (апрель 2026, 19.04, task36) — частично закрыто
- [x] **`pyproject.toml`**, **`requirements-dev.txt`**, **`.pre-commit-config.yaml`**
- [x] Вынесение Pydantic-схем в **`app/schemas/`** (роутеры без inline **`BaseModel`**)
- [x] Миграция **`t7u8v9w0x1yb`**: **`tasks`/`site_projects`** — **`log_events`** вместо **`logs`**, лимит переноса **500** записей; фронт и API
- [x] **structlog** + **`app/logging_config.py`**, **`LOG_JSON`** / **`LOG_LEVEL`**, воркер **`worker_process_init`**
- [x] Задел под интеграционные тесты: **`tests/conftest.py`**, **`tests/factories.py`**, маркер **`integration`**; CI **`pytest -m "not integration"`**
- [x] **task37 (23.04):** по-роутерные API happy-path тесты в `tests/api/test_*_api.py` (CRUD + 404/422 + базовые регрессии `tasks/projects`), `tests/api/conftest.py` (autouse моки + eager Celery), удалён `test_routers_happy_path.py`
- [x] **taskco (22.04):** `add_log` в `pipeline.py` переведён на `LogEvent` + `append_log_event`; `read_log_events`/`read_step_results` подключены в `app/api/tasks.py` и `app/api/projects.py`; добавлены `tests/workers/test_process_generation_task_integration.py`, `test_run_pipeline_minimal_happy_path`, `tests/api/test_routers_crud.py`; CI: `ruff check app tests`, `ruff format --check app tests`, `pytest --cov-fail-under=55`; исправлено **1060** ruff-нарушений (347 авто + 39 ручных: `B904`, `E711`/`E712`, `E722`, `F841`/`B007`, `RUF046`/`RUF059`); bugfix `warnings: List[str] = []` NameError в `preview_project`; `alembic/env.py` SET→SET LOCAL для таймаутов
- [ ] Полный **`ruff check app/`** по legacy-коду и целевое **coverage API** (см. task36) — в бэклоге

### task42: Декомпозиция pipeline.py (апрель–май 2026)
- [x] **Превратить `app/services/pipeline.py` (2579 строк) в пакет `app/services/pipeline/`** — чисто структурный рефакторинг, поведение не меняется:
  - Модули: `context.py`, `registry.py`, `runner.py`, `assembly.py`, `persistence.py`, `vars.py`, `llm_client.py`, `errors.py`, `steps/` (12 файлов по доменам)
  - Критерий: ни один файл > 400 строк; все тесты проходят; реальная задача воспроизводит артефакт
  - План в **`task42.md`** — 7 инкрементальных шагов, каждый green-тесты после коммита
- [x] Добавить типизированный `PipelineContext` с геттерами `step_output`/`serp`/`outline`/`draft`/`html`/`meta_raw`
- [x] Иерархия ошибок `PipelineError` → `LLMError`, `SerpError`, `ParseError`, `ValidationError`, `StepTimeoutError`, `BudgetExceededError`
- [x] Интерфейс шага `PipelineStep` Protocol + `StepResult` + `StepPolicy` (retry/skip per-step)
- [x] Перенести 21 `phase_*` в `app/services/pipeline/steps/*` и переключить `PHASE_REGISTRY` на `_legacy_phase_adapter`
- [x] **task45 / Шаг 4:** `PipelineContext` перенесён в `pipeline/context.py`, финализация вынесена в `pipeline/assembly.finalize_article`
- [x] **task46:** финализирован контракт `finalize_article` (без internal rollback/notify/fail-state), success-notify перенесён в `runner.py`, добавлены `tests/services/test_finalize_article.py`
- [x] **task47:** выполнен аудит step-классов без правок runtime (`task46-audit.md`): registry/policy/error-mapping/side-effects/ctx-getters
- [x] **task48:** закрыты критичные разрывы после task47 — `setup_template_vars` вынесен в `template_vars.py`, `llm_client` маппит ошибки в `LLMError`, `outline/meta/assembly` используют `ParseError/ValidationError`, `test_pipeline_e2e_smoke.py` исправлен (`auto_mode=True` + step-level monkeypatch), добавлен `tests/services/test_pipeline_errors.py` (retry/skip/finalize-fail + pause-инвариант `serp_review`)
- [x] Перенести `run_pipeline`/`run_phase` из `legacy` в `pipeline/runner.py` и удалить временный legacy-adapter слой (финал task42/task43; коммит `addd0da`, апрель 2026)

### Приоритет 1: Стабильность pipeline
- [x] **task52 (22.04.2026):** смягчение зависаний LLM-шагов — **`LLM_REQUEST_TIMEOUT`/`STEP_TIMEOUT_MINUTES`**, **`LLM_MODEL_TIMEOUTS`**, ретраи **`generate_text`** до 2 попыток, backoff 5/10 с для gateway/timeout; OpenRouter **`LLM_MODEL_FALLBACKS`** + лог смены модели в **`llm_client`**; **`runner._call_with_timeout`** на **`ThreadPoolExecutor`** + **`step_deadline`** для exclude-retry; **`tasks.celery_task_id`**, **`enqueue_task_generation`**, revoke в **`cleanup_stale_tasks`** и при **`force-status` fail`** — см. **`CURRENT_STATUS.md`**, **`task52.md`**
- [x] **task47 follow-up (P0):** typed error-mapping для LLM-call path (через `llm_client` → `LLMError`) включён и покрыт тестами ошибок (`test_pipeline_errors.py`)
- [x] **task47 follow-up (P1, частично):** `StepPolicy` для optional fact-check этапов (`content_fact_checking`, `structure_fact_checking`) приведён к явному `skip_on=(LLMError, ParseError)`; для `image_*` сохранён режим без retry
- [ ] **Quality Gate** — автовалидация вывода каждого LLM-шага
  - Функция `validate_step_output(step_name, result)` в pipeline.py
  - Проверки: min length, HTML tags, JSON validity, маркеры обрезки
  - Автоматический retry шага при невалидном выводе (до 2 раз)
  - Поля `min_output_length` и `validation_rules` в модели Prompt
- [ ] **Fallback-модель** — переключение на резервную модель при сбое основной *(частично: **task52** — маршрутизация через **`LLM_MODEL_FALLBACKS`** / **`extra_body.models`** на OpenRouter + лог «fallback to …»; остаётся per-prompt **`fallback_model`** в БД и **`GLOBAL_FALLBACK_MODEL`**)*
  - Поле `fallback_model` в модели Prompt
  - `GLOBAL_FALLBACK_MODEL` в config
  - Логирование факта переключения *(UI-лог уже есть при расхождении `response.model` с запрошенной)*
- [ ] **Dead Letter Queue улучшение** — retry from last step для stale задач
  - UI кнопка "Resume from last step" для stale-задач
- [x] **Pipeline cleanup (микро):** внешний импорт приватного `_auto_approve_images` закрыт переносом helper в `runner.py`; добавлены module-level пояснения для `vars.py`/`template_vars.py` (task50, commit `c11e092`)
- [x] **`docx_step` decision:** зафиксировано N/A by design — DOCX остаётся post-export (`docx_builder` + export endpoints), не runtime-step пайплайна

### Приоритет 2: Контроль качества контента
- [ ] **Target Word Count** — явное указание длины статьи
  - Поле `target_word_count` в модели Task (0 = авто)
  - Множитель 1.1-1.3x от avg_word_count конкурентов
  - Логирование разницы actual vs target
- [ ] **Метрики качества статей** — readability, keyword density, heading count
  - Поля в GeneratedArticle: readability_score, keyword_density, heading_count, internal_links_count
  - Отображение в UI как карточки

### Приоритет 3: Оптимизация скорости
- [ ] **Параллельные шаги анализа** — ThreadPoolExecutor для 3 аналитических агентов
  - ai_structure_analysis, chunk_cluster_analysis, competitor_structure_analysis — параллельно
  - final_structure_analysis — точка синхронизации
  - Сокращение времени pipeline на ~40-60% на аналитическом этапе

---

## Q3 2026 (Июль — Сентябрь) — Публикация и интеграции

### WordPress auto-publish
- [ ] Сервис `app/services/publisher.py` с классом WordPressPublisher
- [ ] Поля в модели Site: wp_url, wp_username, wp_app_password, auto_publish, publish_status
- [ ] Опциональный шаг STEP_PUBLISH после STEP_META_GEN
- [ ] UI настройки публикации per-site
- [ ] `published_url` в GeneratedArticle

### Аналитика стоимости
- [ ] Breakdown по моделям и шагам pipeline
- [ ] Сохранение prompt_tokens/completion_tokens в step_results
- [ ] Графики расходов в дашборде (по дням/неделям)
- [ ] Средняя стоимость статьи

### UX улучшения
- [ ] WYSIWYG-редактор статей (PUT /api/articles/{id})
- [ ] Превью статьи в iframe (sandboxed)
- [ ] Клонирование задач и промптов
- [ ] Bulk-операции: массовый delete/retry/export
- [ ] A/B сравнение версий промптов (side-by-side diff + метрики)

### Webhook API
- [ ] Поле `webhook_url` в модели Site
- [ ] POST-callback после завершения задачи
- [ ] Глобальный webhook как fallback

---

## Q4 2026 (Октябрь — Декабрь) — Масштабирование и новые возможности

### Rate Limiter
- [ ] `app/services/rate_limiter.py` на базе Redis (token bucket)
- [ ] Конфигурация: LLM_REQUESTS_PER_MINUTE, LLM_TOKENS_PER_MINUTE
- [ ] Graceful waiting вместо hard fail

### Генерация изображений
- [x] Midjourney через GoAPI + ImgBB: `image_prompt_generation` → `image_generation` → пауза ревью → `image_inject`
- [x] `image_prompt_generation` формирует промпт по каждому MULTIMEDIA-блоку (type/description/purpose/parent_title/location)
- [x] Парсер **`image_utils.extract_multimedia_blocks`**: мультиязычные ключи MULTIMEDIA, строка/список, встройки в текст Content и др., fallback сканирования сырого outline в **`phase_image_prompt_gen`** (март 2026, см. `docs/CURRENT_STATUS.md`)
- [ ] Поддержка других провайдеров (DALL-E / Stable Diffusion) через интерфейс `ImageGeneratorBase`
- [ ] Опциональная оптимизация изображений (например, конверсия/сжатие) перед вставкой
- [ ] Доп. типы картинок (например, hero-image не из MULTIMEDIA блоков)

### Планировщик генерации (Scheduler)
- [ ] Модель ScheduledTask: cron_expression, keyword_source, site_id, author_id
- [ ] Celery Beat задача по крону создаёт задачи из CSV/списка
- [ ] UI вкладка «Планировщик»

### Мультиязычная генерация
- [ ] Чекбокс «Генерировать на языках: [de, fr, es, ...]» при создании задачи
- [ ] Автоматическое создание дочерних задач (parent_task_id)

---

## Q1 2027 (Backlog) — Долгосрочные идеи

- [ ] RAG-интеграция через Supabase pgvector (экспертные знания в pipeline)
- [ ] Экспорт в Google Docs / Sheets
- [ ] A/B тестирование целых pipeline-конфигураций (не только промптов)
- [ ] Мульти-tenant архитектура (разные команды, разные API ключи)
- [ ] Расширение кэш-стратегии (семантический matching близких keyword, warming, метрики hit-rate)
- [ ] Продвинутый мониторинг (Prometheus + Grafana)
- [ ] CI/CD pipeline (GitHub Actions → auto-deploy на VPS)

---

## Принципы приоритизации

1. **Стабильность > Фичи** — Quality Gate и Fallback-модель важнее новых возможностей
2. **Revenue impact** — WordPress publishing ускоряет цикл публикации
3. **Developer experience** — улучшения UI и инструментов экономят время команды
4. **Масштабируемость** — Rate Limiter и параллельные шаги нужны при росте объёмов