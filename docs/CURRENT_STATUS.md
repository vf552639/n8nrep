# ТЕКУЩИЙ СТАТУС ПРОЕКТА

**Дата последнего обновления:** апрель 2026 (**task55**, коммит **`HEAD`**: exclude-words retry оставлен только в `final_editing` — в upstream-шагах `primary_generation`, `primary_generation_about`, `improver`, `primary_generation_legal` переход на `call_agent` без `call_agent_with_exclude_validation`; обновлены `app/services/pipeline/steps/draft_step.py`, `app/services/pipeline/steps/legal_step.py`; цель — убрать дублирующие LLM-ретраи и снизить стоимость. Ранее **task54**, коммит **`08fa216`**: NUL-санитизация (`app/utils/text_sanitize.py`, `scraper.py`, `serp_step.py`) и обработка OpenRouter 402 с adaptive downscale `max_tokens` + `InsufficientCreditsError` в `llm.py`/`pipeline.errors`; тесты `tests/unit/test_text_sanitize.py`, `tests/services/test_llm_402_downscale.py`. До этого: **task53 E**, **task52**, **task50**, **task48**, **task47**, **task46**, **task45**, **task43**, **taskco**, **task37**, **task41**, **task40**)

---

### Апрель 2026 — task55: exclude-words retries только в `final_editing`

**Контекст:** `call_agent_with_exclude_validation` использовался в пяти шагах (`primary_generation`, `primary_generation_about`, `improver`, `primary_generation_legal`, `final_editing`) и создавал лишние дорогие повторы LLM-вызовов. При этом `final_editing` уже имеет пост-обработку `ExcludeWordsValidator.remove_violations()`, которая детерминированно удаляет остаточные запрещённые слова.

**Сделано**
- `app/services/pipeline/steps/draft_step.py`: в `PrimaryGenStep`, `PrimaryGenAboutStep`, `ImproverStep` вызовы `call_agent_with_exclude_validation(...)` заменены на `call_agent(..., variables=ctx.template_vars)`.
- `app/services/pipeline/steps/legal_step.py`: в `PrimaryGenLegalStep` аналогично заменён вызов на `call_agent(...)`.
- Из `StepResult.extra` в этих шагах удалено поле `exclude_words_violations` (сохранены word-count метрики).
- `app/services/pipeline/steps/final_editing_step.py` и `app/services/pipeline/llm_client.py` не менялись — exclude-words retry и финальный regex-strip остаются в финальном шаге.

**Ожидаемый эффект:** меньше парных повторов на длинных Sonnet-вызовах в upstream-шагах и снижение стоимости при сохранении гарантий по exclude-words на финальном HTML.

---

### Апрель 2026 — task54: NUL-санитизация и OpenRouter 402

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

### Апрель 2026 — task53 E: страницы проекта, БД-таймаут и диагностика ошибок

**Контекст (план `task53.md`, раздел E):** длинные проекты падали на странице с обрезанным сообщением в логе проекта (**`[:200]`** от **`str(exception)`**); гипотеза — глобальный **`statement_timeout=60000`** мс на соединении SQLAlchemy обрывал тяжёлые коммиты с разросшимся JSONB **`step_results`**; любая ошибка пайплайна трактовалась как «skip page» и продвижение **`current_page_index`**, что для инфраструктурных сбоев БД нежелательно.

**`app/database.py`**
- В **`connect_args["options"]`** для движка: **`-c statement_timeout=600000`** (10 минут), чтобы worker-пайплайн реже получал **`canceling statement due to statement timeout`** на крупных **`UPDATE tasks`**.

**`app/workers/tasks.py` — `process_project_page`**
- **`OperationalError`**, **`DBAPIError`** вокруг **`run_pipeline`**: **`db.rollback()`**, повторная загрузка **`SiteProject`** / **`Task`**; задача страницы — **`pending`** (та же строка **`Task`** для повторного запуска), проект — **`pending`**; в **`project.log_events`** — краткое сообщение + хвост traceback (до 4000 символов во второй записи); **`advance_project.apply_async(args=[project_id, False], countdown=60)`** и **`return`** (без немедленного **`advance_project.delay`** в конце функции).
- Прочие исключения пайплайна: в **`project_task.error_log`** сохраняется **traceback** (хвост до 8000 символов), не только текст исключения.
- Сообщение **«Page … FAILED»** в лог проекта: **первая строка** из **`error_log`** (до 500 символов) + **`task_id=`** для открытия задачи в UI.

**Связь с остальным планом task53:** пункты **A–D** (таймауты LLM, fallback-модели, Executor step-timeout, **`celery_task_id`** + revoke) уже закрыты коммитом **`d78c5b8`** (**task52**); ротация **`log_events`** на уровне задачи (**E.3**, last 500) уже в **`app/schemas/jsonb_adapter.py`** / **`persistence.add_log`**.

---

### Апрель 2026 — task52: зависания LLM-шагов, таймауты и revoke Celery

**Контекст:** длинные вызовы (напр. `gpt-5-mini` с reasoning и большим контекстом) + ретраи `generate_text` и exclude-words выходили за **`STEP_TIMEOUT_MINUTES`** / stale в Beat; **`SIGALRM`** в worker-потоке не срабатывал; после **`stale`** / force-fail worker продолжал ждать HTTP.

**Конфиг (`app/config.py`)**
- **`LLM_REQUEST_TIMEOUT`**: дефолт **600** с.
- **`STEP_TIMEOUT_MINUTES`**: **30**; **`PIPELINE_STEP_TIMEOUT_SECONDS`**: **1800**.
- **`LLM_MODEL_TIMEOUTS`**: строка вида `model=seconds,...` — пер- модельный HTTP-таймаут (хелпер **`timeout_for_model`** в **`app/services/llm.py`**).
- **`LLM_MODEL_FALLBACKS`**: строка `primary=fb1|fb2` — в **`generate_text`** в **`extra_body.models`** для OpenRouter provider routing.

**`app/services/llm.py`**
- **`generate_text`**: `timeout=None` → эффективный таймаут через **`timeout_for_model(model)`**; **`max_retries=2`**; backoff для 502/504/timeout **5·(attempt)** (5 с, 10 с); при настроенных fallback — **`extra_body={"models": [model, *fallbacks]}`** без дубля primary в списке fallback.

**`app/services/pipeline/runner.py`**
- **`_call_with_timeout`**: **`ThreadPoolExecutor(max_workers=1)`** + **`future.result(timeout=...)`** → **`StepTimeoutError`** (ветка SIGALRM удалена).
- Перед шагом: **`ctx.step_deadline = monotonic() + timeout_sec`**.

**`app/services/pipeline/context.py`**
- Поле **`step_deadline: float | None`** для бюджета exclude-retry.

**`app/services/pipeline/llm_client.py`**
- Таймаут вызова: **`timeout_for_model(prompt.model)`** вместо фиксированного глобального.
- В лог **`response_received`**: пометка **`⚠ fallback to <actual_model>`**, если ответная модель ≠ запрошенной.
- **`call_agent_with_exclude_validation`**: перед следующим exclude-retry — выход, если **`monotonic() > ctx.step_deadline`**, с предупреждением в лог.

**Celery / БД**
- Модель **`Task.celery_task_id`** (String 64, index), миграция **`x9y8z7w6v5u4_add_celery_task_id_to_tasks.py`**.
- **`app/services/queueing.py`**: **`enqueue_task_generation(db, task)`**, **`revoke_generation_celery_task(id)`**.
- **`app/api/tasks.py`**: все **`process_generation_task.delay`** (кроме **`chain`** в start-all / start-selected) заменены на **`enqueue_task_generation`**; при **`POST .../force-status`** с **`action=fail`** — **`revoke_generation_celery_task`** до смены статуса.
- **`process_generation_task`**: в начале записывает **`task.celery_task_id = self.request.id`**.
- **`process_project_page`**: перед **`run_pipeline`** — то же для **`project_task`** (страницы проекта).
- **`cleanup_stale_tasks`**: после перевода в **`stale`** (heartbeat и step-running timeout) — **`celery_app.control.revoke(..., terminate=True, signal="SIGTERM")`**, если **`celery_task_id`** задан.

**Тесты:** **`tests/services/test_runner_call_timeout.py`** (main thread + worker thread), **`tests/services/test_llm_timeouts_fallbacks.py`**.

**Оговорка:** **`future.result(timeout)`** не убивает поток с активным HTTP; прерывание обеспечивают httpx-таймаут и revoke.

---

### Апрель 2026 — task50: сверка плана после удаления legacy

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

### Апрель 2026 — task48: стабилизация pipeline runner + e2e smoke

**Контекст:** после task47 оставались риски в policy/error-path и два «живых» дефекта в `tests/services/test_pipeline_e2e_smoke.py` (патч не в те bindings шагов и запуск без `auto_mode=True`, что приводило к `paused` на `serp_review`).

**Сделано**
- **Split vars/template_vars:** `setup_template_vars` перенесён из `app/services/pipeline/vars.py` в `app/services/pipeline/template_vars.py`; шаги и `app/services/pipeline/__init__.py` переведены на новый импорт.
- **Typed error mapping:** `app/services/pipeline/llm_client.py` теперь маппит ошибки `generate_text(...)` и отсутствие активного prompt в `LLMError` (`raise ... from e`).
- **Ошибки в шагах/assembly:**
  - `outline_step.py`: невалидный JSON от `final_structure_analysis` → `ParseError`;
  - `meta_step.py`: невалидный JSON от `meta_generation` → `ParseError`;
  - `assembly.py`: пустой assembled HTML → `ValidationError`; strict fact-check fail → `ValidationError`; невалидный `meta_generation` JSON → `ParseError`;
  - docstring `finalize_article()` обновлён под фактические типы исключений.
- **StepPolicy (runner-aware):**
  - `SerpStep`: `retryable_errors=(SerpError, LLMError), max_retries=1`;
  - `StructureFactCheckStep` и `ContentFactCheckStep`: `skip_on=(LLMError, ParseError)`;
  - LLM-генерирующие шаги (`draft/final_editing/legal`) подняты до `max_retries=2`.
- **e2e-smoke fixes (`tests/services/test_pipeline_e2e_smoke.py`):**
  - запуск `run_pipeline(..., auto_mode=True)`;
  - monkeypatch для `call_agent`/`call_agent_with_exclude_validation` перенесён на step-level bindings (`outline_step`, `draft_step`, `meta_step`, `html_assembly_step`, `image_prompts_step`, `final_editing_step`, `legal_step`), чтобы не утекать в реальный `generate_text`.
- **Новые тесты ошибок:** добавлен `tests/services/test_pipeline_errors.py`:
  - retry `LLMError` до успеха (3-я попытка при `max_retries=2`);
  - `ParseError` в fact-check шаге с `skip_on` → `skipped`, pipeline может продолжаться;
  - `ValidationError` из `finalize_article` → `task.status=failed` + `error_log`;
  - pause-инвариант: при `auto_mode=False` после SERP задача уходит в `paused` с `_pipeline_pause.reason="serp_review"`, `competitor_scraping` ещё не выполнен.

**Статус**
- Фиксы task48 закрывают критичные разрывы между policy и runtime-path, а также делают e2e-smoke корректным с точки зрения pause-семантики runner.

---

### Апрель 2026 — task45 (Шаг 4): Context + Assembly, статус

**Сделано**
- `PipelineContext` теперь определяется в `app/services/pipeline/context.py` (конструктор + геттеры `step_output` / `serp` / `outline` / `draft` / `html` / `meta_raw`).
- `run_pipeline` в `app/services/pipeline/runner.py` завершает пайплайн через `finalize_article(ctx)` из `app/services/pipeline/assembly.py`.
- В `assembly.py` используются живые helper-ы `pick_structured_html_for_assembly` / `pick_html_for_meta` и `completed_step_body`.
- Для стабильности monkeypatch-тестов в `app/services/pipeline/__init__.py` добавлены/расширены реэкспорты: `settings`, `generate_text`, `fetch_serp_data`, `scrape_urls`, `notify_task_success`, `notify_task_failed`, а также helper API пайплайна.

**Итог**
- Шаг 4 как структурный этап закрыт: `context` и `assembly` выделены, раннер использует `finalize_article`.
- Детали по финализации контракта и тестам вынесены в отдельный шаг task46.

---

### Апрель 2026 — task46: контракт `finalize_article` + unit-тесты

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

### Апрель 2026 — task47: аудит step-классов (без правок кода)

**Артефакт**
- Добавлен отчёт `task46-audit.md` в корне репозитория (snapshot-аудит A–G).

**Ключевые выводы аудита**
- Регистрация шагов: `STEP_REGISTRY` содержит 21/21 шага; для всех пресетов (`full/category/about/legal`) `missing=[]`.
- Ограничение по размеру: все `steps/*.py` <= 400 LOC.
- Выявлен P0-риск: `retryable_errors=(LLMError,)` объявлен во многих шагах, но `LLMError` фактически не бросается в текущем call-path (`llm_client`), из-за чего retry-policy для LLM-шагов по сути «мёртвая».
- Выявлены P1/P2-зоны: raw `Exception/ValueError` в pipeline-слое, default-policy в `image_*`, низкая adoption `ctx.*` геттеров, неоднозначные `ctx.db.commit()` внутри ряда шагов.

**Открыто после аудита**
- Это осознанно только документационный шаг; исправления P0/P1/P2 идут отдельными PR по action-items из `task46-audit.md`.

---

### Апрель 2026 — task43: декомпозиция pipeline (A–E, F1–F10)

**Контекст:** после выделения каркаса `app/services/pipeline/` и плана task42 выполнен основной перенос логики из `app/services/_pipeline_legacy.py` в пакет с шагами.

**A. Baseline e2e smoke**
- Добавлен `tests/services/test_pipeline_e2e_smoke.py` с `test_run_pipeline_full_preset_smoke` (full preset, 14 шагов, `GeneratedArticle`/status/step_results ассёрты).

**B. Удаление битых shim-шагов**
- Удалены старые `steps/*_step.py` shim-файлы, которые пытались unpack `None` из `phase_*`.
- `steps/__init__.py` переведён на контролируемые импорты актуальных step-модулей.

**C–E. Перенос утилит и контекста**
- Реализованы реальные модули: `pipeline/persistence.py`, `pipeline/vars.py`, `pipeline/template_vars.py`, `pipeline/llm_client.py`, `pipeline/context.py`, `pipeline/assembly.py`.
- `PipelineContext` больше не наследуется от legacy.
- Сборка статьи вынесена в `finalize_article(ctx)` в `pipeline/assembly.py`.

**F1–F10. Перенос 21 phase-функции в step-классы**
- Добавлены step-файлы по доменам: `serp_step.py`, `outline_step.py`, `meta_step.py`, `html_assembly_step.py`, `final_editing_step.py`, `image_prompts_step.py`, `image_gen_step.py`, `image_inject_step.py`, `draft_step.py`, `legal_step.py`.
- В `legacy` добавлен `_legacy_phase_adapter(step_name)`: берёт step из `STEP_REGISTRY`, вызывает `run(ctx)` и сохраняет `StepResult` через `save_step_result`.
- `PHASE_REGISTRY` полностью переключён на `_legacy_phase_adapter(...)`; `def phase_*` в `legacy` удалены.
- `_auto_approve_images` перенесён в `steps/image_gen_step.py`; `run_pipeline` в `legacy` использует его оттуда.

**Результат текущего этапа**
- `STEP_REGISTRY` содержит все 21 pipeline-шага.
- В `app/services/pipeline/steps/*.py` нет файлов > 400 строк.
- Legacy-сценарий запуска сохранён (runner по-прежнему `legacy.run_pipeline`), но логика шагов уже выполняется через новый пакет.

---

### 22 апреля 2026 — taskco: wire-up и quality gates

**Контекст:** закрытие оставшихся пробелов по task36: использование JSONB-адаптеров в рантайме, более реалистичные интеграционные тесты Celery/pipeline, и включение жёстких CI-гейтов по coverage.

**Wire-up `LogEvent` / `jsonb_adapter`**
- **`app/services/pipeline.py`**: `add_log()` переведён на **`LogEvent`** + **`append_log_event`** (вместо ручной сборки dict).
- **`app/api/tasks.py`**: чтение JSONB через **`read_step_results`** / **`read_log_events`**; при **`rerun-step`** запись лога — через **`append_log_event`**.
- **`app/api/projects.py`**: выдача **`log_events`** через **`read_log_events`**; вычисление прогресса и `current_step` из **`read_step_results`**; лог approve-page — через **`append_log_event`**.

**Тесты**
- Новый интеграционный файл: **`tests/workers/test_process_generation_task_integration.py`**:
  - `test_process_generation_task_happy_path`
  - `test_process_generation_task_llm_failure`
  (eager Celery + валидация `task.log_events` через **`LogEvent`**).
- **`tests/services/test_pipeline_smoke.py`**: добавлен **`test_run_pipeline_minimal_happy_path`** (реальный `run_pipeline` с минимальным custom-планом и заглушкой LLM).
- Новый API-файл: **`tests/api/test_routers_crud.py`** — CRUD/404/422 паттерн для **`tasks`**, **`projects`**, **`templates`**.

**CI / coverage**
- **`.github/workflows/ci.yml`**:
  - `ruff check app tests`
  - `ruff format --check app tests`
  - `pytest --cov=app --cov-fail-under=55`
- **`pyproject.toml`**: добавлен блок **`[tool.coverage.report]`** (`skip_empty`, `exclude_lines`).

**Дополнительные исправления (taskco §5, 22.04)**

- **`alembic/env.py` — SET→SET LOCAL:** таймауты `statement_timeout` / `lock_timeout` теперь выставляются через **`SET LOCAL`** (а не `SET`), что ограничивает их действие только текущей транзакцией и не затрагивает следующие соединения пула.
- **`app/api/projects.py` — bugfix `preview_project`:** отсутствовала инициализация `warnings: List[str] = []` перед первым `append`; при некоторых сочетаниях параметров возникал `NameError`. Добавлена инициализация в начале функции.

**Ruff — исправление legacy-долга (`app/` и `tests/`, taskco §5)**
- Исправлено **1060** нарушений ruff в кодовой базе:
  - **347** авто-исправлений: сортировка импортов, `UP006`/`UP045` (typing modernization, `List`/`Optional` → встроенные), лишние пробелы.
  - **39** ручных: `B904` raise-from в except-блоках, `E711`/`E712` (`.is_(None)`/`.is_(True)` вместо `== None`/`== True`), `E722` bare `except:` → `except Exception:`, `F841`/`B007` неиспользуемые переменные, `RUF046`/`RUF059`.
- **`pyproject.toml`**: добавлены глобальные исключения (`B008` FastAPI Depends, `RUF001`/`RUF002` русский unicode, `SIM`-стиль), per-file-ignore `F403`/`F405` для `pipeline.py`.

**Ограничение (осознанно):**
- Включённые ruff-гейты на весь `app/tests` выявляют legacy-долг в старом коде; это отдельный этап cleanup, не блокирующий фиксацию wire-up/тестовых паттернов taskco.

---

### 22 апреля 2026 — task42: план декомпозиции pipeline.py

**Контекст:** `app/services/pipeline.py` разросся до **2579 строк** и совмещает пять несвязанных обязанностей: оркестрация, 21 phase-функция, построение `PipelineContext`, подготовку переменных, сборку `GeneratedArticle`. Цель — чисто структурный рефакторинг без изменения поведения.

**Целевая структура:** пакет `app/services/pipeline/` с модулями:
- `__init__.py` — публичный re-export (`run_pipeline`, `PipelineContext`, `apply_template_vars`)
- `context.py`, `registry.py`, `runner.py`, `assembly.py`, `persistence.py`, `vars.py`, `llm_client.py`, `errors.py`
- `steps/` — 12 файлов по доменам (serp, outline, image×3, draft, legal, final_editing, html_assembly, meta, docx-stub)

**Критерий готовности:** ни один файл > 400 строк; все тесты проходят; реальная задача воспроизводит артефакт.

**План (7 шагов, инкрементально):** инвентаризация/якорные тесты → пакет с legacy re-export → вынос persistence/vars/llm_client → base-interface/registry/errors → PipelineContext+assembly → перенос шагов по группам → новый runner + удаление legacy.

Подробный план — в **`task42.md`** в корне репозитория.

---

### 23 апреля 2026 — Этап 1: task37 (API happy-path тесты)

**Контекст:** вместо одного параметризованного smoke-теста по GET роутерам добавлен набор по-роутерных happy-path тестов для API с CRUD-сценариями и базовыми регрессиями по `tasks/projects`.

**Тестовая инфраструктура**
- **`tests/api/conftest.py`**: autouse-моки внешних сервисов (`llm` / `serp` / `scraper`), eager-настройка Celery, очистка `structlog.contextvars`, отключение worker health-check в API-тестах, привязка `factory_boy` к `api_db_session`.
- **`tests/factories.py`**: расширены фабрики (`ProjectFactory`, `BlueprintFactory`, `BlueprintPageFactory`, `PromptFactory`, `TemplateFactory`, `LegalPageTemplateFactory`, `ArticleFactory`) для покрытия CRUD и сценариев по роутерам.
- Для локального прогона API-тестов требуется dev-набор зависимостей (`factory-boy`, `pytest-asyncio`): `pip install -r requirements.txt -r requirements-dev.txt`.

**API test suite**
- Удалён legacy-файл **`tests/api/test_routers_happy_path.py`**.
- Добавлены роутерные файлы:  
  **`tests/api/test_health_api.py`**, **`test_dashboard_api.py`**, **`test_logs_api.py`**, **`test_sites_api.py`**, **`test_authors_api.py`**, **`test_templates_api.py`**, **`test_prompts_api.py`**, **`test_legal_pages_api.py`**, **`test_blueprints_api.py`**, **`test_articles_api.py`**, **`test_settings_api.py`**, **`test_tasks_api.py`**, **`test_projects_api.py`**.
- Корневой тест приложения перенесён в **`tests/test_app_routes.py`**.
- Добавлены сценарии регрессий: удаление задачи с повторным `404`, `delete-selected` для задач/проектов, archive/force-delete/reset-status для проектов.

**Документация**
- Обновлены **`docs/Roadmap.md`** и **`docs/PROJECT_OVERVIEW.md`** (замена упоминания `test_routers_happy_path` на пакет роутерных API-тестов из task37).

---

### 19 апреля 2026 — Этап 1: фундамент качества (task36)

**Контекст:** снижение регрессий за счёт единого места для Pydantic-схем, задела под интеграционные тесты на Postgres, структурированных логов и переименования JSONB-логов выполнения.

**Инструментарий:** **`pyproject.toml`** (ruff, pytest, mypy на **`app/services/llm.py`**, **`json_parser.py`**, **`meta_parser.py`**), **`requirements-dev.txt`** (pytest, httpx, factory-boy, ruff, pre-commit, structlog и др.), **`.pre-commit-config.yaml`**.

**Схемы API:** **`app/schemas/`** — **`task`**, **`project`**, **`site`**, **`author`**, **`article`**, **`template`**, **`legal_page`**, **`blueprint`**, **`prompt`**, **`settings`**, **`serp_config`**, плюс контракты JSONB: **`step_result`**, **`log_event`**, **`jsonb_adapter`**, **`project_keywords`**. Роутеры **`app/api/*.py`** импортируют модели отсюда; **DoD task36 §1.2:** в каталоге **`app/api/`** нет подклассов **`BaseModel`** (в т. ч. **`app/api/tasks.py`** — только **`from app.schemas.task import ...`**, см. **«22 апреля 2026 — Этап 1: доводка»**).

**БД — `log_events`:** миграция **`t7u8v9w0x1yb`** (revises **`s6t7u8v9w0xe`**): **`tasks.log_events`**, **`site_projects.log_events`**; перенос из **`logs`** с усечением до **500** элементов; ORM **`app/models/task.py`**, **`app/models/project.py`**; запись в **`app/services/pipeline.py`** (**`add_log`**, лимит **500**), **`app/api/tasks.py`**, **`app/api/projects.py`**, **`app/workers/tasks.py`** (**`_append_project_log`**). Ответ **`GET /api/tasks/{id}`** отдаёт **`log_events`**.

**Structlog:** **`app/logging_config.py`** — связка structlog ↔ stdlib **`logging`**, отдельный классический **`FileHandler`** на **`logs/app.log`** (страница **Logs** в UI по-прежнему читает текстовый файл); консоль — JSON при **`LOG_JSON=true`**.

**Тесты и CI:** **`tests/conftest.py`** — при **`TEST_DATABASE_URL`** накатывается **`alembic upgrade head`**, фикстура **`db_session`** с откатом транзакции; **`pytest -m "not integration"`** в **`.github/workflows/ci.yml`** (Postgres/Redis сервисы, переменные **`SUPABASE_*`**, **`OPENROUTER_API_KEY`**, **`API_KEY=""`**). Интеграционные тесты: **`pytest -m integration`** при поднятом **`db-test`** или своей БД.

**Ограничения текущей итерации:** полный **`ruff check app/`** по старому коду не вычищен; в CI **`ruff`** ограничен **`app/schemas/`**, **`app/logging_config.py`**, **`app/workers/celery_app.py`**. Целевое покрытие **`app/api/`** из task36 — в работе (частично: smoke **GET**, см. **«22 апреля 2026 — Этап 1: доводка»**).

---

### 22 апреля 2026 — Этап 1: доводка (tasks API, smoke-тесты, DoD 1.2)

**Контекст:** закрытие регрессии после **`logs` → `log_events`**, устранение дублирования Pydantic-моделей в **`app/api/tasks.py`**, минимальные HTTP-smoke-тесты и явный прогон миграций в CI.

**`app/api/tasks.py`**
- **`GET /api/tasks/{id}`** и **`POST /api/tasks/{id}/rerun-step`** используют только **`task.log_events`** (в ответе — ключ **`log_events`**; при rerun запись в том же формате, что **`add_log`** в **`pipeline.py`**: **`ts`**, **`level`**, **`msg`**, опционально **`step`**, лимит **500**, **`flag_modified(task, "log_events")`**).
- Все тела запросов по задачам импортируются из **`app/schemas/task.py`** (**`TaskCreate`**, **`FetchUrlMetaRequest`**, **`UpdateStepResultRequest`**, **`StartSelectedRequest`**, **`ForceStatusRequest`**, **`RerunStepRequest`**, **`ApproveSerpUrlsRequest`**, **`ApproveImagesRequest`**, **`RegenerateImageRequest`**); **`SerpConfig`** — в **`app/schemas/serp_config.py`** (через **`TaskCreate`**). В **`app/api/`** нет inline-**`BaseModel`**.

**Тесты и CI**
- **`tests/conftest.py`**: **`api_db_engine`**, **`api_db_session`**, **`async_api_client`** — **`httpx.AsyncClient`** + **`dependency_overrides[get_db]`** на транзакцию с откатом; URL БД: **`TEST_DATABASE_URL`** или **`SUPABASE_DB_URL`**; без доступного Postgres связанные тесты **skip**.
- **`tests/api/test_routers_happy_path.py`**: один параметризованный тест — smoke **GET** по **15** путям (все **`include_router`** из **`app/main.py`** + **`/api/health/*`** в одном списке; корень **`GET /`** — в **`tests/api/test_app_routes.py`**).
- **`.github/workflows/ci.yml`**: шаг **`alembic upgrade head`** перед **`pytest`** на сервисе Postgres.

**Без изменений относительно плана task36:** массовые CRUD/404/422 по роутерам; **`pytest -m "not integration"`** по-прежнему не запускает **`@pytest.mark.integration`** (в т. ч. **`tests/services/test_pipeline_smoke.py`**); **`ruff check app/`** целиком в CI не включён.

---

### 21 апреля 2026 — Legal: `primary_generation_legal`, inject, критичные переменные

**Контекст:** у **`LegalPageTemplate`** контент образца может быть **plain text** или **HTML** (**`content_format`**), есть **`notes`**. Промпт **`primary_generation_legal`** и подстановки в пайплайне синхронизированы с моделью данных и UI.

**Backend — `app/services/legal_reference.py`**
- Стартовые ключи: **`legal_reference`**, **`legal_reference_html`** (тот же текст; совместимость со старыми промптами в БД, где осталось **`{{legal_reference_html}}`**), **`legal_reference_format`** (**`text`** / **`html`**), **`legal_template_notes`**, **`legal_variables`**.
- Для **`LEGAL_PAGE_TYPES`**: **`page_type_label`** — человекочитаемый тип (словарь **`PAGE_TYPE_LABELS`**, иначе **`title()`** от slug); выставляется **до** раннего **`return`** при **`use_serp`**, чтобы тип страницы был в контексте и при SERP.
- После резолва шаблона: **`substitute_legal_html`** подставляет **`site.legal_info`** в **`content`**, в переменные пишутся формат, **`notes`**, merge **`variables`** + **`legal_info`** в JSON **`legal_variables`**.

**Pipeline — `app/services/pipeline_constants.py`**, **`call_agent` в `app/services/pipeline.py`**
- **`CRITICAL_VARS["primary_generation_legal"]`**: **`keyword`**, **`language`**, **`country`**, **`page_type_label`**, **`legal_reference`**, **`legal_reference_format`**, **`legal_variables`**.
- **`CRITICAL_VARS_ALLOW_EMPTY`**: пустая **`legal_reference`** (генерация без образца) не помечается как «missing critical».

**Seed — `scripts/seed_prompts.py`**
- Обновлён текст **`primary_generation_legal`** под **`{{legal_reference}}`**, **`{{legal_reference_format}}`**, **`{{legal_template_notes}}`**, **`{{page_type_label}}`**.
- Агент в **`PROMPTS_FORCE_UPDATE`** — при **`python scripts/seed_prompts.py`** активная запись в БД получает тело из seed.

**Frontend — `frontend/src/pages/LegalPagesPage.tsx`**, **`frontend/src/pages/PromptsPage.tsx`**
- Редактор контента legal-шаблона: **`<textarea>`** при **Plain text**, **Monaco** при **HTML**.
- Variable Explorer: новые описания переменных legal (в т. ч. алиас **`legal_reference_html`**).

**Тесты:** **`tests/test_legal_reference_inject.py`**.

---

### 21 апреля 2026 — task41: пользовательские URL конкурентов для проекта

**Контекст:** для страниц проекта конкуренты по умолчанию берутся только из SERP (DataForSEO / SerpAPI). Нужно вручную задать дополнительные URL на **`SiteProject`**, смержить их с органикой SERP, убрать дубли **по домену**, затем передать объединённый список в существующий **`phase_scraping`** (**`scrape_urls`**).

**База данных и модель**
- Таблица **`site_projects`**: колонка **`competitor_urls`** (**JSONB**, **`NOT NULL`**, default **`[]`**).
- Миграция **`v0a1b2c3d4e5_add_competitor_urls_to_site_projects`** (`down_revision`: **`u8v9w0x1y2zc`**).
- Модель **`app/models/project.py`** — поле **`SiteProject.competitor_urls`**.

**Утилиты — `app/services/url_utils.py`**
- **`normalize_url(raw)`** — trim, при отсутствии схемы **`https://`**, отбрасывание при пустом **`netloc`**.
- **`domain_of(url)`** — хост в lower case, без префикса **`www.`**.
- **`merge_urls_dedup_by_domain(primary, extra)`** — порядок: сначала уникальные по домену из **`primary`**, затем из **`extra`**; второй элемент кортежа — список user-URL, отброшенных как дубль домена относительно уже встреченных.

**Схемы — `app/schemas/project.py`**
- **`SiteProjectCreate.competitor_urls`**: опционально, до **50** строк после нормализации; невалидные URL отбрасываются.
- **`SiteProjectCloneBody.competitor_urls`**: опционально; при клоне без поля в новый проект пишется **`[]`** (список с исходного проекта не копируется).
- **`SiteProjectResponse`**: поле **`competitor_urls`**.

**API — `app/api/projects.py`**
- **`POST /api/projects`**: **`competitor_urls=list(project_in.competitor_urls or [])`** при создании **`SiteProject`**.
- **`POST /api/projects/{id}/clone`**: **`competitor_urls`** из тела, если передано; иначе **`[]`**.
- **`GET /api/projects`**, **`GET /api/projects/{id}`**: в JSON добавлено **`competitor_urls`**.

**Pipeline — `app/services/pipeline.py`, `phase_serp`**
- После успешного **`fetch_serp_data`**, до **`ctx.task.serp_data = serp_data`**: если у задачи есть **`project_id`** и у проекта непустой **`competitor_urls`**, нормализованные user-URL мержатся с **`serp_data["urls"]`** через **`merge_urls_dedup_by_domain`**.
- В **`serp_data`** дополнительно: **`user_competitor_urls`**, **`user_competitor_duplicates`**; лог шага SERP с количеством и дублями.
- В **`serp_summary`** (результат шага в **`step_results`**): **`user_competitor_urls_count`**, **`user_competitor_duplicates`**.

**Frontend**
- **`ProjectsPage.tsx`** (модалка **Create Generative Project**): textarea **Competitor URLs**, парсинг **`parseUrls`** (строка / запятая, max **50**), поле **`competitor_urls`** в payload.
- **`ProjectDetailPage.tsx`**: read-only список сохранённых URL.
- Типы и API: **`SiteProjectCreatePayload`**, **`Project`**, **`ProjectClonePayload`** — **`competitor_urls?`**.

**Тесты**
- **`tests/unit/test_url_utils.py`** — кейсы merge/normalize.
- **`tests/services/test_pipeline_smoke.py`** — **`test_phase_serp_merges_project_competitor_urls`** (**`@pytest.mark.integration`**).
- **`tests/api/test_projects_api.py`** — **`test_create_project_with_competitor_urls`**.
- **`tests/factories.py`** — у **`ProjectFactory`** задано **`competitor_urls=[]`**.

---

### 20 апреля 2026 — Markup only: создание проекта без Target Site

**Контекст:** нужна генерация «только разметка» (content-only) без привязки к реальному сайту и без HTML-обёртки (head / header / footer). Колонка **`site_projects.site_id`** остаётся **NOT NULL** — миграции БД не требуются.

**Backend — `app/api/projects.py`**
- Константа **`MARKUP_ONLY_SITE_KEY = "__markup_only__"`** и **`_resolve_site_or_markup_only(db, target_site, country, language, use_site_template)`**: при непустом **`target_site`** — обычный **`_resolve_site`** и переданный флаг обёртки; при **`None`** / пустой строке (после нормализации валидатором) — **`_resolve_site(db, MARKUP_ONLY_SITE_KEY, …)`** (создание или переиспользование placeholder-строки в **`sites`**) и **`use_site_template=False`**.
- **`SiteProjectCreate.target_site`**, **`ProjectPreviewRequest.target_site`** — **`Optional[str] = None`**; **`field_validator`** приводит пустую строку к **`None`**.
- **`create_project`**: резолв сайта и флага через **`_resolve_site_or_markup_only`**; в **`SiteProject`** пишется **`use_site_template`** с учётом результата helper.
- **`preview_project`**: без **`target_site`** — readonly по **`MARKUP_ONLY_SITE_KEY`**, **`effective_use_site_template = False`**, предупреждение в **`warnings`** про markup-only; в ответе **`site.use_site_template`** и **`has_template`** согласованы с этим режимом.
- **`clone_project`**: если в теле передан **`target_site`** (не **`None`** после strip) — **`_resolve_site_or_markup_only`**; если поле опущено — по-прежнему сайт исходного проекта и логика **`use_site_template`** из тела/источника.
- **`SiteProjectCloneBody`**: нормализация **`target_site`** (пустая строка → **`None`**, наследование сайта при clone).

**Frontend**
- **`frontend/src/api/projects.ts`**: **`SiteProjectCreatePayload.target_site?: string`**.
- **`frontend/src/pages/ProjectsPage.tsx`** (модалка **Create Generative Project**): состояние **`markup_only`**; чекбокс **Markup only**; при включении — **`site_id: ""`**, **`use_site_template: false`**, скрыты блоки **Target Site** и **Use site HTML template**; **Preview** / **Start** без сайта; в API не отправляется **`target_site`**, **`use_site_template: false`**; валидация и подсказка у **Author** учитывают режим.

---

### 20 апреля 2026 — task40: гарантированные meta-теги и блок автора в финальном HTML

**Контекст:** для страниц проектов без активной обёртки сайта (или при шаблоне без плейсхолдеров `title/description`) часть non-main страниц уходила в экспорт без корректного `<head>` (`<title>`, `<meta name="description">`). Также в финальном документе отсутствовали данные автора, хотя они используются в LLM-контексте.

**Backend — `app/services/template_engine.py`**
- Добавлена **`ensure_head_meta(html, title, description)`**: для полноценной страницы обновляет/вставляет `<title>` и `<meta name="description">` в `<head>`; для HTML-фрагмента оборачивает в минимальный `<!doctype html><html><head>...`.
- Добавлена **`render_author_footer(author)`**: формирует HTML-секцию `<section class="author-info">` со строками **Автор / Страна / Код страны / Город / Язык / Биография** (только непустые поля, с HTML-экранированием).

**Backend — `app/services/pipeline.py` (сборка `GeneratedArticle.full_page_html`)**
- После `generate_full_page(...)` всегда вызывается **`ensure_head_meta(...)`**: и при `None` (шаблон не применён), и при успешной обёртке (подстраховка шаблонов без плейсхолдеров мета).
- В финальный документ инжектится author-footer: если есть `ctx.task.author_id`, блок вставляется перед первым `</body>`, иначе добавляется в конец строки.

**Backend — `app/services/site_builder.py`**
- Добавлен warning-лог при fallback на `article.html_content`, если `full_page_html` пустой: помогает оперативно ловить регрессы сборки full-page HTML.

**Authors: модель / API / UI**
- Модель **`app/models/author.py`**: поле **`country_full`** (полное название страны).
- Миграция Alembic: **`u8v9w0x1y2zc_add_country_full_to_authors.py`**.
- Схема **`app/schemas/author.py`**: **`country_full`** в `AuthorCreate`.
- API **`app/api/authors.py`**: `GET /api/authors` возвращает `country_full`; `POST/PUT` читают и сохраняют `country_full`.
- UI **`frontend/src/pages/AuthorsPage.tsx`** и типы **`frontend/src/types/author.ts`**: добавлено поле формы **«Страна (полное название...)»** с привязкой к `country_full`.

**Тесты**
- Новый unit-файл: **`tests/services/test_template_engine.py`** — кейсы для `ensure_head_meta` (обёртка/обновление/идемпотентность/экранирование) и `render_author_footer`.
- Обновлён API-тест авторов: **`tests/api/test_authors_api.py`** (payload с `country_full`).

---

### 19 апреля 2026 — HTML-экспорт страниц (MODX / Source)

**Контекст:** экспорт в DOCX искажает разметку при переносе в MODX; контент-менеджерам нужен **чистый HTML** тела страницы (как в **`GeneratedArticle.html_content`**, без обёртки сайта), с сохранением комментариев **`<!-- MEDIA: ... -->`** для ручной вставки изображений.

**Backend — `app/services/html_export.py`**
- **`resolve_export_body(task, article, for_html_export=...)`** — приоритет тела: **`article.html_content`** → извлечение из **`full_page_html`** (первый из **`main`** / **`article`** / **`body`**) → шаги в порядке **`image_inject`** → **`html_structure`** → **`final_editing`** → … (как **`pick_structured_html_for_assembly`** / бывший fallback в DOCX). При **`for_html_export=True`**: не-HTML в **`final_editing`** → **`HtmlExportNotReadyError`** (в API **409** «Page not ready for HTML export»).
- **`clean_html_for_paste`** — лёгкая чистка через BeautifulSoup (**`html.parser`**), без ломки HTML-комментариев; сериализация **`soup.decode(formatter="html5")`**.
- **`GET /api/tasks/{task_id}/export-html`** — только при **`task.status == "completed"`**, иначе **409**; **`Content-Type`**: **`text/html; charset=utf-8`**; **`Content-Disposition`**: **`{slug}.html`** (slug из **`blueprint_pages.page_slug`** или keyword); ответ с заголовком **`X-Export-Source`** (ключ источника тела).
- **`GET /api/projects/{project_id}/export-html`** — query **`mode`**: **`zip`** (по умолчанию) — архив **`{project_name}.html.zip`** с **`index.html`** (оглавление-ссылки) и **`{slug}.html`** на каждую завершённую страницу; **`concat`** — один файл **`{project_name}.html`** со склейкой и разделителями **`<!-- ===== PAGE: {slug} ===== -->`**. Права/условия как у **`/export-docx`** (нет завершённых страниц → **400**).

**`app/services/docx_builder.py`** — **`_get_content_from_task`** и экспорт задачи без строки **`GeneratedArticle`** вызывают **`resolve_export_body(..., for_html_export=False)`** (тот же приоритет, без строгого **409** для markdown в **`final_editing`** — DOCX отдаёт plain).

**Frontend** — **`frontend/src/api/tasks.ts`**: **`exportHtml`**, **`exportHtmlUrl`**, **`exportHtmlDownload`**; **`frontend/src/api/projects.ts`**: **`exportHtmlZip`**, **`exportHtmlConcat`**, URL-хелперы; **`TaskDetailPage`**: **Download HTML** / **Copy HTML** (при **`completed`**; **409** → тост; fallback-модалка с **textarea**, если clipboard недоступен); **`ProjectDetailPage`**: меню **Download HTML** — **All pages (ZIP)** / **Single file**.

**Тесты:** **`tests/test_html_export.py`** (пять кейсов для **`clean_html_for_paste`**).

---

### 19 апреля 2026 — Зависшие проекты: force-delete, массовое удаление, reset-status, каскад сайта

**Контекст:** если Celery падает без обработки, проект мог оставаться в **`pending`**/**`generating`** и не удалялся обычным **`DELETE`**. Нужны явные операции восстановления и каскадное удаление сайта с проектами.

**Backend — `app/api/projects.py`**
- **`DELETE /{id}?force=false|true`**: при **`force=False`** — по-прежнему **400**, если статус **`pending`** или **`generating`**. При **`force=True`** — **`_revoke_project_celery_task(project.celery_task_id)`** ( **`celery_app.control.revoke(..., terminate=True)`** ), затем удаление всех **`Task`** с **`project_id`**, удаление **`SiteProject`**.
- **`POST /delete-selected`**: тело **`DeleteSelectedProjectsRequest`** — **`project_ids`**, **`force`** (по умолчанию **`false`**). Без **`force`** активные проекты считаются **`skipped`**; с **`force`** — revoke + удаление для каждого найденного id.
- **`POST /{id}/reset-status`**: только **`pending`**/**`generating`** → **`status = failed`**, **`error_log = "Manually reset — stale task"`**, **`celery_task_id = None`**, revoke; иначе **400**.

**Backend — `app/api/sites.py`**
- **`DELETE /{site_id}?force=false|true`**: при **`force=False`** и наличии задач/проектов — **409** с **`detail`**: **`message`**, **`task_count`**, **`project_count`**, **`projects: [{ id, name, status }]`**.
- При **`force=True`**: для каждого **`SiteProject`** сайта — revoke по **`celery_task_id`**, удаление задач проекта, удаление проекта; затем **`Task`** с **`target_site_id`**, удаление **`Site`**.

**Frontend**
- **`frontend/src/api/projects.ts`**: **`deleteProject(id, { force })`**, **`deleteSelected(ids, { force })`**, **`resetProjectStatus(id)`**.
- **`frontend/src/api/sites.ts`**: **`delete(id, { force })`**.
- **`ProjectsPage.tsx`**: колонка выбора строк (**`enableRowSelection`** как на **`TasksPage`**), панель **«Удалить выбранные»** / **«Снять выделение»**; во вкладке **Archived** — кнопки **Restore** и **Delete** (корзина); при **400** на удалении — модалка с **Force Delete**; при bulk и **`skipped > 0`** — confirm на повтор с **`force: true`**; **`deleteMutation.mutate`** на деталке проекта — аргумент **`{}`** (требование **TS** / TanStack Query).
- **`ProjectDetailPage.tsx`**: кнопка **Delete** всегда; **Reset stuck status** для **`pending`**/**`generating`**; модалка **Force Delete** после **400**; **`deleteMutation.mutate({})`** для обычного удаления.
- **`SitesPage.tsx`**: при **409** — список блокирующих проектов и кнопка **«Удалить сайт вместе со всеми проектами»** → **`force: true`**.

---

### 18 апреля 2026 — Sites API и чекбокс Use site HTML template

**Цель:** UI **Create Generative Project** стабильно отражает наличие HTML-шаблона у сайта (**`sites.template_id`**), в т.ч. после частичного деплоя и при устаревшем кэше React Query; пользователь всегда видит опцию **Use site HTML template** после выбора сайта, даже если шаблона нет (тогда чекбокс недоступен и объяснено поведение).

**Backend — `app/api/sites.py` (`_site_out`)**
- В JSON каждого сайта: **`template_id`**, **`template_name`**, **`has_template`** (`bool(s.template_id)`).

**Frontend — `frontend/src/pages/ProjectsPage.tsx` (модалка создания проекта)**
- Запрос списка сайтов: **`refetchOnMount: "always"`** для ключа **`["sites"]`**.
- При непустом **`site_id`**: **`useQuery`** → **`sitesApi.getOne(id)`** (ключ **`["sites", site_id]`**), **`selectedSite`** = деталка или строка из списка.
- **`siteHasTemplate`** = **`selectedSite?.has_template ?? Boolean(selectedSite?.template_id)`**.
- **Показ блока с чекбоксом:** при **`formData.site_id`** (не только при **`siteHasTemplate`**).
- **`onSiteChange`:** **`use_site_template`** = **`has_template ?? Boolean(template_id)`** у выбранного сайта из списка (нет шаблона → **`false`** по умолчанию).
- **`useEffect`:** если **`siteHasTemplate`** ложен, а **`use_site_template`** ещё **`true`** (например, после дозагрузки деталки) — сброс в **`false`**.
- **Чекбокс:** **`disabled={!siteHasTemplate}`**; подсказка при отсутствии шаблона: *«No HTML template assigned to this site…»*; при наличии шаблона — прежний текст про отключение обёртки.

**Тесты**
- **`tests/test_sites_api.py`** — проверки **`has_template`** для сайта с шаблоном и без.

**Docker: когда «на фронте ничего нового»**
- Сервис **`frontend`** собирает **`npm run build`** **внутри образа** (нет volume с исходниками). После правок TS/React: **`docker compose build --no-cache frontend`**, затем **`docker compose up -d --force-recreate frontend`**.
- По умолчанию UI на хосте: **`http://localhost:3001`** (переменная **`FRONTEND_HOST_PORT`** в **`.env`** / compose; не путать с **`8000`** бэкенда или локальным **`npm run dev`**).
- Проверка, что строка попала в сборку:  
  **`docker compose exec frontend sh -c 'grep -l "Use site HTML template" /app/dist/assets/*.js'`**  
  (ожидаются в т.ч. **`ProjectsPage-*.js`**, **`ProjectDetailPage-*.js`**). Чанк **`ProjectsPage`** подгружается при заходе на **`/projects`** — нужен жёсткий refresh (**Cmd+Shift+R**) / инкогнито при закэшированном **`index.html`**.

---

### 18 апреля 2026 — Language: INITCAP и защита на фронте

**Проблема (закрыта):** в дропдаунах **Language** дублировались значения с разным регистром (**`French`** / **`french`**); при выборе нижнего регистра фильтр авторов по **`===`** не находил записей с **`French`**.

**База данных**
- Миграция **`s6t7u8v9w0xe_normalize_language_authors_sites`** (`down_revision`: **`r4s5t6u7v8wd`**): **`UPDATE authors SET language = INITCAP(TRIM(language)) …`**, то же для **`sites`**. **`downgrade`** — пустой (данные нормализованы необратимо без бэкапа).

**Backend**
- **`app/utils/language_normalize.py`** — функция **`normalize_language`** (trim + регистр по словам, в духе INITCAP).
- **`app/api/authors.py`** — **`AuthorCreate`**: **`field_validator("language")`** перед записью.
- **`app/api/sites.py`** — **`SiteCreate`** / **`SiteUpdate`**: валидаторы **`language`**.

**Frontend**
- **`frontend/src/lib/languageDisplay.ts`** — **`normalizeLanguageDisplay`**, **`languageEquals`**.
- **`ProjectsPage.tsx`**: список языков из нормализованных строк; **`filteredAuthors`** — страна в **UPPER**, язык через **`languageEquals`**.
- **`TasksPage.tsx`** (модалка создания задачи): то же для языков и авторов.
- **`SitesPage.tsx`** (модалка добавления сайта): нормализация списка языков из авторов.

**Тесты**
- **`tests/test_language_normalize.py`** — кейсы для **`normalize_language`**.

---

### 18 апреля 2026 — Legal templates: дефолт на Blueprint, override в Project, фолбек в pipeline

**Цель:** три уровня выбора reference-шаблона для legal-страниц: явный выбор в проекте → дефолт страницы блупринта → генерация без reference.

**База данных и модель**
- Таблица **`blueprint_pages`**: колонка **`default_legal_template_id`** (UUID, FK → **`legal_page_templates.id`**, **`ON DELETE SET NULL`**, nullable).
- Миграция **`p2q3r4s5t6ub_add_default_legal_template_to_blueprint_pages`** (`down_revision`: **`n1o2p3q4r5sa`**).
- Модель **`app/models/blueprint.py`** — поле **`BlueprintPage.default_legal_template_id`**.

**Backend — `app/api/blueprints.py`**
- Схема **`BlueprintPageCreate`**: опциональный **`default_legal_template_id`** (строка UUID).
- **`_validate_default_legal_template`**: разрешено только при **`page_type ∈ LEGAL_PAGE_TYPES`**; шаблон должен существовать, **`is_active=True`**, **`page_type`** шаблона совпадает со страницей; при смене **`page_type`** на не-legal колонка обнуляется.
- **`GET /api/blueprints/{id}/pages`**: в каждой странице возвращается **`default_legal_template_id`** (строка или **`null`**).

**Backend — `app/api/legal_pages.py`**
- **`GET /api/legal-pages/for-blueprint/{blueprint_id}`**: для каждого элемента **`legal_page_types`** добавлено **`default_template_id`** — значение с первой страницы блупринта данного **`page_type`** (порядок **`sort_order`**, как и раньше для **`page_title`**).
- Элементы **`templates`** в ответе: **`{ id, name }`** (без отдельного **`title`** — см. блок **«LegalPageTemplate: удаление `title`»** ниже).

**Backend — `app/services/legal_reference.py`**
- **`inject_legal_template_vars`**: после чтения **`project.legal_template_map[page_type]`** (если пусто или нет ключа с непустым значением) — фолбек на **`BlueprintPage.default_legal_template_id`** по **`ctx.task.blueprint_page_id`**; загрузка **`LegalPageTemplate`** с проверкой **`page_type`** и **`is_active`**.

**Frontend**
- **`frontend/src/types/blueprint.ts`**, **`frontend/src/types/template.ts`**: новые поля; **`LEGAL_PAGE_TYPES_SET`** для условного UI.
- **`BlueprintsPage.tsx`**: селект **`page_type`** (article, category, homepage, legal-типы; опция «custom» для нестандартных значений из БД); при legal-типе — дропдаун **Default Legal Template** (`legalPagesApi.getByPageType`).
- **`ProjectsPage.tsx`**: при загрузке **`legal-for-blueprint`** — **`useEffect`** заполняет **`legal_template_map`** дефолтами из **`default_template_id`**, если пользователь ещё не выбрал ни одного шаблона; подсказка под селектом при наличии blueprint-дефолта.

---

### 18 апреля 2026 — LegalPageTemplate: удаление поля `title`

**Цель:** единственный человекочитаемый идентификатор шаблона в списках и формах — **`name`** (плюс **`page_type`**); колонка **`title`** в БД и API убрана.

**База данных**
- Миграция **`q3r4s5t6u7vc_remove_title_from_legal_page_templates`** (`down_revision`: **`p2q3r4s5t6ub`**): **`DROP COLUMN title`** на **`legal_page_templates`**.

**Backend**
- **`app/models/template.py`**: у **`LegalPageTemplate`** нет **`title`**.
- **`app/api/legal_pages.py`**: схемы **`LegalPageCreate`** / **`LegalPageUpdate`** без **`title`**; ответы **`GET /`**, **`GET /by-page-type/...`**, **`GET /{id}`** и элементы **`for-blueprint` → `templates`** без **`title`**; **`POST /`** не записывает **`title`**.

**Frontend**
- **`frontend/src/types/template.ts`**, **`frontend/src/api/legalPages.ts`**, **`LegalPagesPage.tsx`**: форма, таблица и API без **`title`**.
- **`BlueprintsPage.tsx`**: в дропдауне legal-шаблонов отображается только **`name`**.

---

### 18 апреля 2026 — Проект: `use_site_template` (обёртка сайта опционально)

**Цель:** шаблон HTML остаётся привязанным к **`Site.template_id`**, но для конкретного **`SiteProject`** можно отключить использование обёртки: статьи — «сырой» HTML без head/CSS/header/footer; **`sites.template_id`** не меняется (другие проекты того же сайта могут оставаться с обёрткой).

**База данных и модель**
- Таблица **`site_projects`**: колонка **`use_site_template`** (**`BOOLEAN NOT NULL`**, **`DEFAULT TRUE`**).
- Миграция **`r4s5t6u7v8wd_add_use_site_template_to_site_projects`** (`down_revision`: **`q3r4s5t6u7vc`**).
- Модель **`app/models/project.py`** — поле **`SiteProject.use_site_template`**.

**Backend — `app/api/projects.py`**
- **`SiteProjectCreate`**, **`ProjectPreviewRequest`**: **`use_site_template: bool = True`**.
- **`SiteProjectCloneBody`**: опциональный **`use_site_template`**; при отсутствии в теле — копируется с исходного проекта.
- **`POST /api/projects`**, **`GET /api/projects`**, **`GET /api/projects/{id}`** — сохранение и отдача флага.
- **`POST /api/projects/preview`**: эффективный **`has_template`** = наличие активного шаблона у сайта **и** **`use_site_template`**; при **`use_site_template=False`** при активном шаблоне сайта — **`warnings`**: *"Site template disabled for this project. Articles will be raw HTML."*; в **`site`** добавлено **`use_site_template`** (эхо запроса).
- **`POST /api/projects/{id}/clone`** — запись **`use_site_template`** в новую строку.

**Backend — пайплайн и сборка страницы**
- **`app/services/pipeline.py` — `setup_template_vars`**: если у задачи есть **`project_id`** и у проекта **`use_site_template`** ложь — **`site_template_html`** / **`site_template_name`** принудительно пустые (нет **`[SITE TEMPLATE REFERENCE]`** в **`html_structure`**, **`programmatic_html_insert`** получает пустой шаблон → возвращает тело статьи).
- **`app/services/template_engine.py` — `generate_full_page`**: аргумент **`project_id: Optional[str]`**; при отключённом флаге у проекта — **`return None`** → **`GeneratedArticle.full_page_html`** может быть **`NULL`**, контент в **`html_content`**.

**Backend — ZIP**
- **`app/services/site_builder.py`**: для файла в архиве используется **`full_page_html`**, при его отсутствии — **`html_content`**, чтобы проекты без обёртки не давали пустой ZIP.

**Frontend**
- **`SiteProjectCreatePayload`**, типы **`Project`**, **`ProjectPreview.site`**, **`ProjectClonePayload`**: поле **`use_site_template`**.
- **`ProjectsPage.tsx`** (модалка **New Project**): чекбокс *Use site HTML template* только если у выбранного сайта есть **`template_id`**; preview/create передают флаг; бейдж **Template: OFF** в превью при **`use_site_template === false`**.
- **`ProjectDetailPage.tsx`** (**Clone project**): тот же чекбокс и передача в **`cloneProject`**.

---

### 16 апреля 2026 — Защитная инфраструктура: 500 как JSON, миграции, пул БД, Alembic DDL

**Контекст:** инцидент с неприменённой миграцией и **`idle in transaction`** на Supavisor — 500 отдавались как **`text/plain`**, фронт показывал «Network Error»; расхождение ревизии БД и кода не было видно при старте.

**Backend — `app/main.py`**
- Глобальный **`@app.exception_handler(Exception)`**: лог с traceback; ответ **`JSONResponse` 500** с полями **`detail`** (тип исключения + сообщение до 500 символов), **`path`**, **`method`** — axios получает JSON и может показать **`formatApiErrorDetail`** вместо абстрактной ошибки сети.
- Явный проход для **`HTTPException`** и **`RequestValidationError`**, чтобы не подменять штатные 4xx/422.
- **`lifespan`**: при старте приложения вызывается **`verify_migrations()`** — сравнение ревизии в БД (**`MigrationContext.get_current_revision()`**) с **`ScriptDirectory.get_current_head()`** по **`alembic.ini`** от корня репозитория; при расхождении — **`logger.error`** с баннером и подсказкой **`docker-compose exec web alembic upgrade head`**; при успехе — **`logger.info`** `Alembic migrations up to date: <rev>`; при ошибке проверки — **`logger.warning`**. Отдельный **`create_engine`** для проверки с **`dispose()`** после чтения.

**Backend — `app/database.py`**
- **`create_engine`**: **`pool_pre_ping=True`**, **`pool_recycle=300`**, **`pool_size=10`**, **`max_overflow=20`**, **`pool_timeout=30`**, **`connect_args={"options": "-c statement_timeout=600000"}`** (серверный лимит запроса для пула приложения; **23.04.2026 — task53 E**: поднято с **60000** мс из‑за тяжёлых **`UPDATE`** **`step_results`** на длинных страницах проекта — см. раздел **«task53 E»** выше).
- **`get_db()`**: при исключении после **`yield`** — **`db.rollback()`**, затем **`db.close()`** (автокоммит после **`yield`** не добавлялся: в роутерах по-прежнему явные **`db.commit()`**).
- Контекстный менеджер **`db_session()`** — commit / rollback / close для сценариев вне FastAPI (по желанию для воркеров).

**Alembic — `alembic/env.py`**
- В **`run_migrations_online`** перед **`context.run_migrations`**: на соединении **`SET statement_timeout = '300s'`** и **`SET lock_timeout = '15s'`** (через **`sqlalchemy.text`**) — снижает риск обрыва DDL из‑за короткого дефолта пулера при ожидании лока.

**Документация**
- **`.agent/workflows/alembic-migration.md`** — раздел **Troubleshooting** (`pg_stat_activity`, завершение **`idle in transaction`**, разделение DDL и data-миграций, напоминание про лог при старте API).

---

### 15 апреля 2026 — `phase_image_inject`: корректный инжект по `<!-- MEDIA: ... -->`

**Проблема (закрыта):** после `html_structure` в тексте уже нет маркеров `[MULTIMEDIA ...]` — они конвертируются в HTML-комментарии `<!-- MEDIA: ... -->`. Из-за этого `phase_image_inject` не находил маркеры, не вставлял `<figure>` и не очищал хвостовые комментарии.

**Backend (`app/services/pipeline.py`)**
- В `phase_image_inject` regex-очистка маркеров обновлена в двух местах:
  - ветка без одобренных картинок (`if not approved_images`);
  - финальная очистка после инжекта.
- Старый паттерн `r'\[MULTIMEDIA[^\]]*\]'` заменён на `r'<!--\s*MEDIA:.*?-->'` с флагами `re.IGNORECASE | re.DOTALL`.
- Логика вставки изображений переписана:
  - HTML парсится через `BeautifulSoup`;
  - собираются все комментарии `MEDIA:` в порядке появления через `bs4.Comment`;
  - `approved_images[i]` вставляется на место `media_comments[i]`;
  - если картинок больше, чем MEDIA-комментариев, работает fallback: вставка перед последним `<h2>`.
- Удалён устаревший эвристический матчинг по `section_keywords` и заголовкам `h2/h3`.

**Результат**
- Инжект снова синхронизирован с фактическим форматом выхода `html_structure`.
- После шага `image_inject` в HTML не остаются `<!-- MEDIA: ... -->` комментарии без соответствующих изображений.

---

### 15 апреля 2026 — DOCX: тело статьи из шагов без «перехвата» `final_editing`

**Проблема (закрыта):** при пустом **`article.html_content`** (реран, сборка не записалась и т.п.) **`_get_content_from_task`** уходил во внутренний **`from_final()`** и брал **только** результат шага **`final_editing`**, не доходя до **`content_from_step_results_fallback`**, где первым идёт **`html_structure`**. В итоге экспорт статьи/задачи в Word мог отдавать markdown/черновик вместо HTML после **`html_structure`** / **`image_inject`**.

**Backend (`app/services/docx_builder.py`)**
- **`_get_content_from_task`:** если **`article.html_content`** непустой — по-прежнему он; иначе сразу **`content_from_step_results_fallback(task)`** (убрана ветка «только `final_editing`»).
- **`content_from_step_results_fallback`:** порядок ключей **`step_results`** приведён к тому же, что **`pick_structured_html_for_assembly`** в **`pipeline.py`**: **`image_inject`** → **`html_structure`** → **`final_editing`** → **`improver`** → **`interlinking_citations`** → **`reader_opinion`** → **`competitor_comparison`** → **`primary_generation`** / **`primary_generation_about`** / **`primary_generation_legal`**.
- **`_resolve_single_article_body`:** удалён дублирующий второй вызов **`content_from_step_results_fallback`** при наличии **`task`** (источник тела уже полностью закрывается в **`_get_content_from_task`**).

**Примечание:** визуально DOCX по-прежнему «проще» HTML-превью из‑за конвертации **`_html_to_docx_body`** (ограниченный набор тегов → абзацы/заголовки/таблицы и т.д.) — это не регрессия источника контента.

---

### 14 апреля 2026 — SERP URL review: автопарсинг title/description + fallback в pipeline

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

### 13 апреля 2026 — Пауза после SERP: ревью и редактирование URL конкурентов

**Контекст:** между SERP и scraping пользователь должен иметь возможность убрать «мусорные» URL и добавить свои (например из Ahrefs). Аналогия с паузой **`image_review`**, но для одиночных (**не проектных**) задач и со статусом задачи **`paused`**.

**Поведение**
- При **`run_pipeline(..., auto_mode=False)`** после успешного **`save_step_result`** для шага **`serp`** в **`phase_serp`**: в **`step_results`** пишется **`_pipeline_pause: { "active": true, "reason": "serp_review" }`**, **`task.status = paused`**, пайплайн **не** переходит к **`phase_scraping`** (после **`run_phase`** для SERP выполняется **`return`** из **`run_pipeline`**).
- При **`auto_mode=True`** (страницы проекта) пауза **не** выставляется — поведение проектов без изменений.
- В начале **`run_pipeline`** обработка активной паузы **`serp_review`** без **`_serp_urls_approved`**: для ручной задачи — повторный лог и **`return`** (статус **`paused`**); для **`auto_mode`** — автоснятие паузы и пометка approved (защита от неконсистентного состояния).

**База данных и модель**
- Enum PostgreSQL **`task_status`**: новое значение **`paused`**. Миграция **`m9n0o1p2q3re_add_task_status_paused`**: **`ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'paused'`**.
- Модель **`app/models/task.py`**: **`task_status_enum`** включает **`paused`**.

**API (`app/api/tasks.py`)**
- **`GET /api/tasks/{task_id}/serp-urls`** — список URL из **`task.serp_data`** с обогащением из **`organic_results`** (title, description, position/rank, domain, **`manually_added`**), плюс **`paused`** (активна ли пауза **`serp_review`**) и **`keyword`**.
- **`POST /api/tasks/{task_id}/approve-serp-urls`** — тело **`{ "urls": ["https://...", ...] }`** (непустой список). Требуется активная пауза **`serp_review`**; обновляются **`serp_data.urls`** и **`serp_data.organic_results`** (новые URL получают заглушку с **`manually_added: true`**); **`_pipeline_pause.active = false`**, **`_serp_urls_approved = true`**, **`status = pending`**, **`process_generation_task.delay`**.
- **`POST .../force-status`**: допускается также **`paused`** (наряду с **`processing`**, **`stale`**).
- **`POST .../rerun-step`**: допускается также **`paused`**.

**Frontend**
- **`frontend/src/components/tasks/SerpUrlsReviewer.tsx`** — таблица URL, удаление, ручное добавление (**`http://` / `https://`**), кнопка продолжения, бейдж **Manual** для **`manually_added`**.
- **`frontend/src/api/tasks.ts`** — **`getSerpUrls`**, **`approveSerpUrls`**.
- **`TaskDetailPage`**: блок при **`status === "paused"`** и **`_pipeline_pause.reason === "serp_review"`**; опрос задачи каждые 3 с и для **`paused`**; фильтр статуса **Paused** на **`TasksPage`**; **`StatusBadge`** / тип **`Task`** — **`paused`**.

**`PipelineContext` (`pipeline.py`)** — поле **`auto_mode`**, задаётся из **`run_pipeline`**.

---

### 11 апреля 2026 — JSON-парсер, `meta_generation`, Top P в Model Settings (UI)

**Контекст:** доработки по task25 — корректное извлечение title/description из ответа **`meta_generation`**; универсальный парсер JSON без хардкода ключей **`ai_structure_analysis`**; визуальная согласованность Top P при выключенном тоггле.

**`app/services/json_parser.py` — `clean_and_parse_json(text, unwrap_keys=None)`**
- Универсальный парсинг: снятие markdown-ограждений, при ошибке **`json.loads`** — извлечение первого JSON-объекта через **`JSONDecoder().raw_decode`**, затем запасной regex; устойчивость к тексту до/после JSON и к «хвосту» после валидного объекта.
- Размотка вложенного dict **только** при явном **`unwrap_keys`** (для **`phase_ai_structure`** передаётся **`{"intent", "Taxonomy", "Attention", "structura"}`**). Остальные вызовы (в т.ч. **`meta_generation`**, fact-check) получают внешний объект как есть — без ложного «переезда» в первый вложенный dict.

**`app/services/meta_parser.py`**
- **`extract_meta_from_parsed(meta_data)`** — единое извлечение **`title`**, **`description`**, **`h1`** из ответа **`meta_generation`**: списки под ключами **`results`** / **`variants`** (без учёта регистра), затем любой непустой **`list[dict]`**; плоские поля на верхнем уровне; вложенные dict (обёртки вроде **`response`**). Ключи полей ищутся **без учёта регистра** (**`title`/`meta_title`**, **`description`/`meta_description`**, **`h1`/`heading`/`headline`**).
- **`meta_variant_list(meta_data)`** — полный список вариантов для DOCX (тот же приоритет **`results`** / **`variants`**, иначе первый **`list[dict]`**).
- Алиас **`_extract_meta_from_parsed`** = **`extract_meta_from_parsed`**.

**`app/services/pipeline.py`**
- **`phase_meta_generation`:** после **`call_agent`** — debug-лог **`meta_generation raw (first 500): …`** (шаг **`meta_generation`**).
- **Сборка статьи:** после **`clean_and_parse_json`** — debug-лог **`meta_data keys: …`**; **`extract_meta_from_parsed(meta_data)`** → **`title`**, **`description`**, debug-лог **`meta extracted: title=…, desc=…, h1=…`**; при пустом title — fallback на keyword и предупреждение в логе. Полный JSON по-прежнему в **`meta_data`** у статьи.
- Если для **`task_id`** уже есть **`GeneratedArticle`** — **обновление** строки (title, description, **`meta_data`**, HTML, **`full_page_html`**, **`word_count`**, fact-check поля, **`needs_review`**), а не только создание новой.
- **`meta_json_str`** не-строка (edge case) — приводится к JSON-строке перед парсингом.

**`app/services/docx_builder.py`**
- **`_get_all_meta_from_task`:** парсинг шага **`meta_generation`** через **`clean_and_parse_json`**; мета для таблицы/DOCX — **`extract_meta_from_parsed`**; **`all_variants`** — **`meta_variant_list`** (поддержка **`variants`**, произвольных списков вариантов).

**Frontend — `frontend/src/pages/PromptsPage.tsx` (Top P)**
- При выключенном тоггле **`top_p`**: отображение **`0`**, при снятии тоггла — **`top_p: 0`** в **`editState`**; fallbacks **`?? 0`** для поля, слайдера, **`isPromptDirty`**, **`PromptTestPanel`**, сохранения (**`PUT /api/prompts/{id}`** с **`top_p: 0`** при **`top_p_enabled: false`**). Логика **`prompt_llm_kwargs`** / OpenRouter без изменений — при **`top_p_enabled=false`** ключ **`top_p`** в запрос не попадает.

**Тесты:** **`tests/test_json_parser.py`** (перенесены сценарии с прежнего **`tests/test_pipeline.py`** + новые кейсы meta / **`unwrap_keys`**); **`tests/test_meta_parser.py`** — форматы **`results`** / **`VARIANTS`**, flat, вложенные обёртки, приоритет списков.

---

### 8 апреля 2026 — LLM: не передавать `top_p` / penalties в API при `*_enabled = False`; Force Fail/Complete для `stale`

**Проблема (закрыта):** при выключенных тогглах в запрос всё равно уходили **`top_p=1.0`**, **`frequency_penalty=0`**, **`presence_penalty=0`** — часть моделей на OpenRouter ведёт себя иначе, чем при полном отсутствии ключей в теле запроса.

**Backend**
- **`app/services/prompt_llm_kwargs.py`** — **`llm_sampling_kwargs_from_prompt()`**: в словаре для **`generate_text`** всегда есть **`temperature`** (при выключенном тоггле — **0.7**); **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** добавляются **только** если соответствующий **`_*_enabled`**; **`max_tokens`** — по-прежнему только при enabled и **> 0**. **`format_llm_params_log_line`**: в строку лога попадают **freq** / **pres** / **top_p** только если они реально переданы в вызов API (суффикс **`(custom)`**).
- **`app/services/llm.py`** — **`generate_text`**: аргументы **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** — **`Optional[float] = None`**; в **`client.chat.completions.create`** ключи добавляются только при **`is not None`**.
- **`app/api/prompts.py`** — в **`PromptTest`** для сухого **`POST /api/prompts/test`** поля **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** по умолчанию **`None`**, чтобы не дублировать старое поведение «всегда 0 / 1.0» без явной передачи с клиента.

**Задачи (`app/api/tasks.py`)**
- **`POST /api/tasks/{id}/force-status`** (**`complete` | `fail`**): разрешены статусы **`processing`** и **`stale`** (раньше только **`processing`**). Для **`pending`**, **`completed`**, **`failed`** и др. — **400** с текстом **`Only 'processing' or 'stale' tasks can be forced`**. **Актуализация 13.04.2026:** также **`paused`** (SERP URL review) — см. раздел **«13 апреля 2026»** ниже.

**Тесты:** **`tests/test_prompt_llm_kwargs.py`** — отсутствие отключённых ключей в kwargs и обновлённые проверки лога.

---

### 6 апреля 2026 — Pipeline Presets (набор шагов per страница блупринта)

**Проблема (закрыта):** один глобальный режим «SERP / не SERP» для всех страниц без SERP не подходил для About, Legal, Category vs полной статьи.

**База данных и модель**
- Таблица **`blueprint_pages`**: **`pipeline_preset`** (`VARCHAR(20)`, default **`full`**) — одно из: **`full`**, **`category`**, **`about`**, **`legal`**, **`custom`**; **`pipeline_steps_custom`** (JSONB, массив строк `agent_name` или `NULL` для пресетов).
- Миграция **`l6m7n8o9p0qc_add_pipeline_preset_to_blueprint_pages`**: добавление колонок + перенос существующих строк по **`use_serp`** / **`page_type`** / **`page_slug`** (legal → about → category).

**Backend**
- **`app/services/pipeline_presets.py`** — словари пресетов, **`resolve_pipeline_steps`**, **`resolve_steps_from_payload`**, **`pipeline_steps_use_serp`** (по факту наличия шагов SERP/scraping).
- **`app/services/pipeline.py`** — у задачи с **`blueprint_page_id`** список шагов из страницы; **`PHASE_REGISTRY`** + цикл **`run_pipeline`**; в **`step_results`** пишется **`_pipeline_plan: { "steps": [...] }`** для прогресса и UI.
- Пресет **`full`**: полный SEO-путь **без** `interlinking_citations`, image-цепочки и **`content_fact_checking`** (их можно включить только в **`custom`**). **`category`**: SERP + scraping + `final_structure_analysis` + генерация + `final_editing` + `html_structure` + `meta_generation`. **`about`**: **`primary_generation_about`** + **`meta_generation`**. **`legal`**: **`primary_generation_legal`** + **`meta_generation`** (перед вызовом — **`inject_legal_template_vars`**).
- Новые агенты: **`primary_generation_about`**, **`primary_generation_legal`** — константы и **`CRITICAL_VARS`** в **`pipeline_constants.py`**; промпты в **`scripts/seed_prompts.py`** (при вставке — **`max_tokens_enabled`**, **`temperature_enabled`** где задано в seed).
- **`phase_final_editing`**: если нет **`improver`**, fallback на **`primary_generation`**; для **`use_serp=false`** — также **`primary_generation_about` / `primary_generation_legal`**.
- **`phase_html_structure`** / **`phase_meta_generation`** / сборка статьи: выбор HTML из цепочки шагов с учётом about/legal (см. **`pick_html_for_meta`**, **`pick_structured_html_for_assembly`**).
- **`phase_content_fact_checking`**: при **`FACT_CHECK_ENABLED=false`** сохраняется завершённый «skipped»-результат, чтобы **`run_phase`** не вызывал шаг повторно при кастомном списке.
- **`PipelineContext`**: страница блупринта загружается по **`blueprint_page_id`** даже без **`project_id`**; **`all_site_pages`** — по **`blueprint_id`** страницы.

**API**
- **`app/api/blueprints.py`** — в create/update страницы: **`pipeline_preset`**, **`pipeline_steps_custom`**; **`use_serp`** пересчитывается с сервера по резолву шагов.
- **`app/api/projects.py`** — preview страниц: поля **`pipeline_preset`**, **`use_serp`** от резолва.
- **`app/api/tasks.py`** — **`calculate_progress`**: при наличии **`_pipeline_plan.steps`** прогресс = доля завершённых шагов из плана; иначе прежняя эвристика.

**Frontend**
- **`frontend/src/lib/pipelineSteps.ts`** — канонический порядок шагов для custom UI и **`orderedStepKeysFromResults`**.
- **`BlueprintsPage`**: колонка **Pipeline**, выбор пресета и чекбоксы для **`custom`**.
- **`StepMonitor`**: список шагов из **`_pipeline_plan`** или из ключей **`step_results`** (упорядоченно).
- **`PromptsPage`**: агенты **`primary_generation_about`**, **`primary_generation_legal`** в карте и порядке.
- **`TaskDetailPage`**: **Article Review** и **Export DOCX** учитывают черновики about/legal.

**DOCX**
- **`content_from_step_results_fallback`** — добавлены ключи **`primary_generation_about`**, **`primary_generation_legal`**.

**Обратная совместимость:** одиночные задачи без блупринта — как раньше: **`full`** при **`use_serp=true`**, иначе цепочка **`primary_generation` → `final_editing` → `html_structure` → `meta_generation`**. Глобальный **`skip_in_pipeline`** на промпте по-прежнему отключает шаг.

---

### Апрель 2026 — Monaco для HTML: Article Review, Article Detail; ручное сохранение `step_results`

**Backend (`app/api/tasks.py`):**
- **`PUT /api/tasks/{task_id}/step-result`** — тело **`{ "step_name": "<ключ шага из ALL_STEPS>", "result": "<html или текст>" }`**. Шаг должен существовать в **`task.step_results`** со **`status: "completed"`**. Обновляется **`result`**, выставляются **`manually_edited: true`**, **`edited_at`**, пересчитывается **`output_word_count`** (**`count_content_words`**). Предыдущий объект шага добавляется в **`{step_name}_prev_versions`** (как при **rerun**). Ответ **`{"status": "ok"}`**. Для мутации JSONB используется **`flag_modified`**.

**Frontend (`frontend/src/api/tasks.ts`):**
- **`tasksApi.updateStepResult(taskId, stepName, result)`** → **`PUT`** выше.

**`TaskDetailPage.tsx` — вкладка 📝 Article Review:**
- Контент для превью/редактора: **самый «поздний» завершённый шаг** из цепочки **`final_editing` → `improver` → `interlinking_citations` → `reader_opinion` → `competitor_comparison` → `primary_generation` → `primary_generation_about` → `primary_generation_legal`**; бейдж **`Showing: <step>`**, для шагов **`primary_generation*`** дописывается **`(draft)`** где применимо (см. **`TaskDetailPage`**).
- Вкладка доступна, если есть такой шаг **или** активен **test mode** (**`waiting_for_approval`**).
- **Preview** — **iframe** **`srcDoc`** (как раньше). **Source** — **Monaco** (**`@monaco-editor/react`**, `language="html"`, **`vs-dark`**, word wrap, minimap): по умолчанию **read-only**, кнопки **Edit** / **Read only** и **Save** (сохранение в выбранный шаг через **`updateStepResult`** + инвалидация **`task`** / **`task-steps`**).

**`ArticleDetailPage.tsx` — вкладка `html`:**
- Один экземпляр **Monaco**: **`readOnly: !editingHtml`**, значение **`full_page_html || html_content`** в режиме просмотра и **`htmlDraft`** при правке; кнопки **Edit HTML** / **Save** / **Cancel** и **`PATCH /api/articles/{id}`** без изменения контракта.

---

### Апрель 2026 — `llm.py`: стоимость и токены из сырого ответа OpenRouter; логи pipeline

**`app/services/llm.py` (`generate_text`):**
- После **`chat.completions.with_raw_response.create`** тело ответа разбирается через **`json.loads(raw_response.text)`**; из **`usage`** при наличии: **`cost`** (приоритет над заголовком для денег), **`prompt_tokens`**, **`completion_tokens`**, **`total_tokens`**, а также **`prompt_tokens_details.cached_tokens`** и **`completion_tokens_details.reasoning_tokens`** (Prompt Caching / reasoning-модели).
- Если JSON не разобрался: фолбэк **`x-openrouter-cost`**, затем прежняя оценка стоимости по токенам из **`response.usage`**.
- Возврат и **`progress_callback("response_received")`** получают **`usage`** с полями **`cached_tokens`** и **`reasoning_tokens`** там, где они есть в ответе провайдера.

**`app/services/pipeline.py` (`call_agent`, `_on_llm_progress`):**
- Событие **`response_received`**: в лог задачи пишется строка **`[agent] LLM response received (P+C tokens | ⚡ N cached | 🧠 R reasoning, $…)`** — суффиксы **`cached`** / **`reasoning`** только при **> 0**; сумма в долларах с **5** знаками после запятой.

---

### Апрель 2026 — DOCX одиночной статьи/задачи: шапка H1 и строка Title в таблице

**`app/services/docx_builder.py` (`build_single_article_docx`, `_add_simple_article_meta_table`):**
- Первая строка документа (крупный заголовок по центру, Pt(22)): значение **H1** из **`_get_all_meta_from_task(task, article)`**; если пусто — прежний **`display_title`** (`article.title` / ключ / «Article»). Так отделяется **SEO Title** (в таблице) от **H1** страницы.
- Мета-таблица: **Keyword**, **Word Count**, **Title** (meta title из **`_get_all_meta_from_task`**, иначе fallback на **`display_title`**), **Description**. Параметр **`title`** у **`_add_simple_article_meta_table`**.
- При отсутствии **`task`** метаданные из шагов не подтягиваются: шапка и строка Title в таблице совпадают с **`display_title`**.

---

### Апрель 2026 — Model Settings: флаги `*_enabled` (task21), pipeline и гидратация UI

**Проблема (закрыта):** тогглы Max tokens / Temperature / Freq. / Pres. / Top P «угадывались» по числовым значениям; **`isDirty`** и сохранение расходились с ожиданиями; при refetch React Query форма могла рассинхронизироваться.

**База данных и модель**
- Таблица **`prompts`**: колонки **`max_tokens_enabled`**, **`temperature_enabled`**, **`frequency_penalty_enabled`**, **`presence_penalty_enabled`**, **`top_p_enabled`** (boolean, не nullable). Миграция **`k5m6n7o8p9qb_add_prompt_param_enabled_flags`**: после добавления колонок выполняется **`UPDATE`** — начальные значения флагов выводятся из числовых полей (например, **`temperature_enabled`** если **`|temperature - 0.7| > ε`**).
- Одноразовый скрипт повторной синхронизации флагов: **`scripts/migrate_param_flags.py`** (идемпотентный SQL, на случай расхождения после деплоя).

**Backend**
- **`app/services/prompt_llm_kwargs.py`** — **`llm_sampling_kwargs_from_prompt()`**: кастомные **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** и **`max_tokens`** попадают в вызов LLM только при соответствующем **`_*_enabled`**; **`temperature`** всегда (**0.7** при выключенном тоггле). **Актуализация 8.04.2026:** при **`false`** для freq/pres/top_p ключи **не включаются** в запрос к OpenRouter (см. раздел **«8 апреля 2026 — LLM: не передавать…»** выше). Тот же helper с optional overrides используется в **`POST /api/prompts/{id}/test`**.
- **`app/services/pipeline.py`** — **`call_agent`** собирает kwargs через helper; в лог задачи пишется строка **`[agent] LLM params: …`** (**`format_llm_params_log_line`** — только фактически переданные sampling-поля).
- **`app/api/prompts.py`** — **`PromptUpdate`** и **`_prompt_to_response`** включают все **`_*_enabled`**; **`PromptTestContext`** расширен полями для передачи несохранённых параметров из UI при тесте.

**Frontend (`frontend/src/pages/PromptsPage.tsx`)**
- **`paramsEnabledFromPrompt(p)`** — только с серверных **`p.*_enabled`**, без эвристик по числам.
- **`isPromptDirty`** — сравнение всех пяти тогглов с сохранённым промптом и значений только для включённых параметров.
- **`saveMutation`** — **`promptsApi.updateInPlace`** с телом **`_*_enabled`** и значениями по правилам task21.
- **`PromptTestPanel`** — проп **`llm: PromptTestLlmOptions`** (модель + флаги + числа); тест шлёт актуальное состояние формы без обязательного Save.
- **Гидратация:** **`useRef` `syncedPromptIdRef`** — при первом появлении данных для **`fullPrompt.id`** один раз вызываются **`setEditState(buildCleanPromptFromServer(fullPrompt))`** и **`setParamsEnabled(paramsEnabledFromPrompt(fullPrompt))`**; при повторном refetch с **тем же** id локальные правки **не** затираются (нет антипаттерна «флаг внутри **`setEditState`**»). Зависимости эффекта: **`[derivedActiveId, fullPrompt?.id]`**.

**Деплой (напоминание)**
- Сервисы **`web` / `worker` / `beat`** в **`docker-compose`** монтируют **`.:/app`** — Python берётся с **хоста**; после **`git pull`** достаточно перезапуска, образ пересобирать не обязательно (кроме смены **`requirements.txt`**).
- **`frontend`** собирается **в образе** — после смены TS/React нужны **`docker compose build --no-cache frontend`** и **`alembic upgrade head`** на БД.
- Браузер: жёсткое обновление / отключение кэша, чтобы не подтягивался старый **`dist`**.

---

### 3 апреля 2026 — Prompts: сохранение in-place, Model Settings UI, фикс выбора модели

**Backend (`app/api/prompts.py`)**
- **`PUT /api/prompts/{prompt_id}`** — обновление **той же** строки в БД без новой версии и нового UUID; ответ в формате **`GET /{prompt_id}`** (в т.ч. **`updated_at`**), общая сериализация через **`_prompt_to_response()`**.
- Обычное сохранение из UI идёт через **`PUT`**, а не через **`POST /`** (который создаёт новую версию агента).

**Frontend (`frontend/src/api/prompts.ts`, `PromptsPage.tsx`)**
- **`promptsApi.updateInPlace(id, payload)`** → **`PUT /prompts/{id}`**; **`saveMutation`** использует его; после успеха — **`setQueryData(['prompt', id])`**, инвалидация **`['prompts']`**.
- **Гидрация `editState` / `paramsEnabled`:** `useEffect` зависит от **`[derivedActiveId, fullPrompt?.id]`**, а не от ссылки на объект **`fullPrompt`**, чтобы refetch React Query с тем же id **не сбрасывал** локальные правки (в т.ч. выбранную модель). Убран **`justSavedRef`**. **Актуализация (апрель 2026):** гидратация через **`syncedPromptIdRef`** — см. раздел **«Model Settings: флаги *_enabled»** выше.
- Во всех **`setEditState`** при отсутствии `prev` возвращается **`prev`**, а не **`null`**, чтобы не обнулять форму.

**Редизайн Model Settings (визуал, `task20`)**
- Панель: градиент **`bg-gradient-to-b from-[#e8ebef] to-[#d5d9df]`**, заголовок **Model Settings**, один горизонтальный ряд с **`overflow-x-auto`**, **`ToggleSwitch`** (iOS-стиль) для Max. Tokens / Temperature / Freq. / Pres. / Top P, слайдеры с классом **`model-slider`** (кастомный CSS в **`frontend/src/index.css`**), кнопка **Save** — **`bg-blue-600`** с dirty-индикатором.
- Компонент **`frontend/src/components/ToggleSwitch.tsx`**.

**`ModelSelector` и баг «пропали параметры»**
- Выпадающий список рендерится через **`createPortal(..., document.body)`** с **`position: fixed`** по координатам кнопки (обновление на scroll/resize). Иначе родитель с **`overflow-x-auto`** обрезал по вертикали соседние блоки параметров и выпадашку; визуально оставались заголовок и поле **Search models...**.
- Клик вне: учитываются и кнопка, и портальное меню.

---

### 2 апреля 2026 — Pipeline: контекст шага `final_editing`

**`app/services/pipeline.py`, `phase_final_editing`:**
- Из **`editing_context`**, передаваемого в агент **`final_editing`**, убраны строки про **целевой объём по конкурентам** (`Target word count (competitor average): {avg_words}`) и **текущую статистику входного HTML** (слова/символы), чтобы не подталкивать модель к сокращению текста «до среднего по конкурентам».
- Переменные **`avg_words`**, **`input_word_count`**, **`input_char_count`** по-прежнему вычисляются и используются в **`add_log`** и **`save_step_result`** (метрики шага не менялись).

**Актуализация (апрель 2026) — без дублирования HTML/outline в `[CONTEXT]`:**
- **`editing_context`** для **`final_editing`** — **`""`**: текст статьи задаётся только через **`{{result_improver}}`** в user prompt из БД, структура — **`{{result_final_structure_analysis}}`** (из **`task.outline`** и/или **`step_results`**, см. ниже). Раньше тот же HTML и outline дублировались в **`[CONTEXT]`** и конфликтовали с промптом.
- **`call_agent`**: суффикс **`[CONTEXT]`** к user message добавляется только если **`context`** непустой после **`strip()`**.
- **`setup_template_vars`**: для каждого завершённого шага в **`step_results`** выставляется **`result_<ключ_шага>`**, если переменная ещё не задана или пустая (не перезаписывает непустые значения из **`task.outline`**, в т.ч. **`result_final_structure_analysis`**).
- В **`phase_final_editing`** после выбора тела статьи: **`ctx.template_vars["result_improver"] = improved_html`** — для **`use_serp=false`** нет шага **`improver`**, иначе **`{{result_improver}}`** оставался бы пустым.
- **`scripts/seed_prompts.py`**: обновлены system/user для **`final_editing`**; уже существующие строки в БД меняются вручную на странице **Prompts**.

---

### 2 апреля 2026 — DOCX: одиночная статья и одиночная задача

**Backend (`app/services/docx_builder.py`)**
- **`build_single_article_docx(article, task=None)`** — один `.docx`: шапка **H1** (из мета, см. раздел **«DOCX одиночной статьи: шапка H1»** выше), таблица мета (**Keyword**, **Word Count**, **Title**, **Description**), тело из HTML через **`_html_to_docx_body`** или plain через **`_add_plain_text_content`**; общая логика контента с **`_get_content_from_task`** и при необходимости fallback по шагам (**`html_structure` → `final_editing` → `primary_generation`**).
- **`build_task_export_docx(db, task)`** — если есть **`GeneratedArticle`** по **`task_id`**, экспорт через **`build_single_article_docx`**; иначе синтетическая статья из **`content_from_step_results_fallback`** (тот же приоритет шагов).

**API**
- **`GET /api/articles/{article_id}/download?format=docx`** — Word; без **`format`** или **`format=html`** — прежнее поведие (HTML). Неподдерживаемый **`format`** → **400**. Нет контента для DOCX → **400**.
- **`GET /api/tasks/{task_id}/export-docx`** — DOCX по задаче; **404** если задачи нет, **400** если нет ни статьи, ни черновика в **`step_results`**.

**Frontend**
- **`ArticleDetailPage`:** кнопка **Export DOCX** (`articlesApi.downloadBlob(id, "docx")`, blob + API key).
- **`TaskDetailPage`:** **Export DOCX** в шапке (рядом с Force Complete/Fail), видима при **`status === "completed"`** или непустом **`step_results.final_editing.result`**; **`tasksApi.exportDocx(id)`** (как у проектов).

---

### 2 апреля 2026 (вторая итерация) — Инфраструктура, API, React UI

**Инфраструктура**
- **Streamlit удалён:** файл **`frontend/app.py`** удалён, зависимость **`streamlit`** убрана из **`requirements.txt`**.
- **Docker Compose:** сервис **`frontend-react`** переименован в **`frontend`** (сборка из **`./frontend`**, порт **3000**). Отдельного контейнера Streamlit больше нет.
- В compose остаётся **5 сервисов:** `web`, `worker`, `beat`, `redis`, `frontend`.

**Backend**
- **`GET /api/tasks`:** ответ **`{ "items": [...], "total": N }`** (пагинация). Query: **`skip`**, **`limit`**, **`status`**, **`search`** (подстрока по **`main_keyword`**), **`site_id`**. Устранён дубликат ключа **`page_type`** в JSON элемента.
- **`PATCH /api/articles/{id}`:** правка **`html_content`**, опционально **`title`** / **`description`**; пересчёт **`word_count`** через **`count_content_words`**; при правке HTML сбрасывается **`full_page_html`**. В **`GET /api/articles/{id}`** в ответ добавлено поле **`full_page_html`**.
- **`GET /api/dashboard/stats`:** дополнительно **`cost_by_day`** — сумма **`total_cost`** по календарным дням (UTC) за последние ~30 дней для задач со статусом **`completed`** (группировка по дате **`updated_at`**).

**Frontend (React)**
- **`SiteDetailPage` (`/sites/:id`):** полная форма сайта (**name, domain, country, language, is_active**, выбор **`template_id`**, **legal_info** JSON); блок **глобальных HTML-шаблонов** с Add / Edit (Monaco) / Delete через **`/api/templates`** (шаблоны общие для всех сайтов, не вложенные в `/sites/.../templates`).
- **`TasksPage`:** серверная пагинация (**50** строк на страницу), поиск с debounce на бэкенде, фильтр по сайту через **`site_id`**; низ таблицы — Previous / Next и счётчик записей.
- **`ArticleDetailPage`:** **Download HTML**, **Export DOCX** (blob через axios с API key), **Edit HTML** (Monaco) + **Save** через **`PATCH`** (раньше ссылка «Export Word» с **`?format=docx`** не работала на бэкенде — см. раздел **DOCX: одиночная статья** выше).
- **`DashboardPage`:** столбчатый график (Recharts) по **`cost_by_day`**, если есть данные.
- **`TaskDetailPage`:** запрос **`GET /tasks/{id}/images`** выполняется и при паузе **`image_review`**, даже если вкладка открывается до финального статуса шага (улучшение загрузки превью).
- **`ProjectDetailPage`:** для задачи со статусом **`failed`** — кнопка **Retry page** (вызов **`POST /tasks/{id}/retry`**).
- **Маршрут `/seo-setup` удалён** (файл **`SeoSetupPage.tsx`**); нижний пункт **SEO Setup** в сайдбаре убран; заголовок сайдбара: **«SEO Content»**.

---

### 2 апреля 2026 — Проекты: DOCX, additional keywords, формат meta_generation

**Проблема (исправлено):** ответ `meta_generation` в виде `{"results": [{Title, Description, H1, Trigger}, …]}` не содержит ключей `title`/`description` на верхнем уровне — в **`pipeline.py`** при сборке статьи теперь из **первого элемента** `results` берутся Title/Description (и при отсутствии — предупреждения в лог); в **`GeneratedArticle.title` / `description`** попадают эти значения, в **`meta_data`** сохраняется **полный JSON** со всеми вариантами.

**Модель и миграция**
- **`site_projects.project_keywords`** (JSONB): пул доп. ключей, результат кластеризации по slug страниц, `unassigned`, при необходимости `clustering_model` / стоимость. Миграция **`j4k5l6m7n8oa_add_project_keywords_to_site_projects`**.

**Backend**
- **`app/config.py`:** `CLUSTERING_MODEL`, `MAX_PROJECT_KEYWORDS` (100).
- **`app/services/keyword_clusterer.py`** — один LLM-вызов, JSON-ответ с распределением ключей по страницам blueprint.
- **`POST /api/projects/cluster-keywords`** — preview кластеризации (без записи в БД).
- **`SiteProjectCreate`** / создание проекта: опционально **`project_keywords`**; клонирование копирует поле.
- **`process_project_page`** (`app/workers/tasks.py`) — слияние **`assigned_keywords`** в **`Task.additional_keywords`** с дедупликацией.
- **`app/services/docx_builder.py`** — один DOCX на проект: титул, оглавление, на каждую страницу таблица мета (Slug, Filename, Meta Title, Meta Description, **H1**, Keyword, Additional Keywords, Word Count; при **нескольких** вариантах в `results` — дополнительные строки Variant N Title/Description/H1/Trigger); контент из `html_content` или plain text / fallback `final_editing`.
- **`GET /api/projects/{id}/export-docx`** — требуется ≥1 задача со статусом `completed`; `Content-Disposition` с именем проекта.
- Зависимость **`python-docx`** (`requirements.txt`).

**Frontend**
- **`ProjectsPage`:** поле Additional Keywords, кнопка Cluster Keywords, превью распределения; при создании передаётся **`project_keywords`**.
- **`ProjectDetailPage`:** кнопка **Export DOCX** при `completed_tasks > 0` (рядом с CSV).

---

### 1 апреля 2026 — Templates, Legal Pages, связь Site → Template

**Модели и БД**
- Таблица **`templates`**: переиспользуемые HTML-оболочки (name, html_template, description, preview_screenshot, is_active, timestamps). Таблица **`site_templates`** удалена; миграция **`i3d4e5f6a7b8`** переносит данные и проставляет **`sites.template_id`**.
- Таблица **`legal_page_templates`**: country, page_type (privacy_policy, terms_and_conditions, cookie_policy, responsible_gambling, about_us), title, html_content, variables (JSONB), notes, is_active; **UNIQUE(country, page_type)**.
- **`sites`**: **`template_id`** (FK → templates), **`legal_info`** (JSONB) — company_name, contact_email, address и т.д. для legal-страниц.

**Backend**
- **`app/api/templates.py`** — `GET/POST/PUT/DELETE /api/templates`; удаление шаблона запрещено, если на него ссылаются сайты (**409**).
- **`app/api/legal_pages.py`** — CRUD `/api/legal-pages`, метаданные **`GET /api/legal-pages/meta/page-types`** (статический путь до `/{id}`).
- **`app/api/sites.py`** — без вложенных `/sites/{id}/templates`; **`GET/PATCH /api/sites/{id}`**, в списке **`template_name`**.
- **`app/services/template_engine.py`** — шаблон по **`Site.template_id`**; **`get_template_for_reference`** возвращает HTML и **name** из **`Template`**.
- **`app/services/legal_reference.py`** — в **`inject_legal_template_vars`** / **`setup_template_vars`**: при **use_serp=false** и **`page_type`** из legal-набора подставляются образец (**`legal_reference`** / **`legal_reference_html`** — один текст, плейсхолдеры `{{...}}` из **`legal_info`**), **`legal_variables`** (JSON). Расширение (**`legal_reference_format`**, **`legal_template_notes`**, **`page_type_label`**) — см. раздел **«21 апреля 2026»** выше.

**Frontend**
- **`/templates`** — `TemplatesPage`: список шаблонов (в т.ч. **sites_count**), модалка name / description / HTML (Monaco).
- **`/sites`** — `SitesPage`: сайты, колонка Template; создание с выбором **`template_id`**.
- **`/sites/:id`** — `SiteDetailPage`: выбор шаблона, редактор **`legal_info`** (JSON).
- **`/legal-pages`** — `LegalPagesPage`: таблица + фильтр country, модалка с типами страниц и Variables JSON.
- Sidebar: **Templates**, **Sites**, **Legal Pages** — отдельные пункты.

**Промпты:** в списках переменных — legal: **`legal_reference`**, **`legal_reference_html`**, **`legal_variables`** и далее по **`PromptsPage.tsx`** (актуализация **21.04.2026**).

**Превью проекта:** проверка наличия HTML-шаблона у сайта — через **`site.template_id`** и активный **`Template`** (не **`SiteTemplate`**).

---

## ✅ Выполнено (MVP v1.0 — полностью рабочая система)

### Инфраструктура
- [x] FastAPI backend с 10 API роутерами + Swagger
- [x] Защитная инфраструктура API и БД (**16.04.2026**): JSON **500**, **`verify_migrations`** при старте, пул engine + **`get_db` rollback**, таймауты в **`alembic/env.py`** — см. раздел **«16 апреля 2026»** выше
- [x] SQLAlchemy ORM + Alembic миграции (см. `alembic/versions/`)
- [x] Celery + Redis (worker + beat)
- [x] Docker-compose (5 сервисов: web, worker, beat, redis, frontend на порту 3000)
- [x] Аутентификация через X-API-Key header
- [x] CORS настройка через .env
- [x] Health-check endpoint для worker

### Core Pipeline (шаги по пресету / custom)
- Порядок выполнения задаётся **`_pipeline_plan`** (**`app/services/pipeline_presets.py`** + **`app/services/pipeline.py`**); см. раздел **«6 апреля 2026 — Pipeline Presets»** выше. Ниже — все возможные фазы; в конкретной задаче может быть подмножество.
- [x] SERP Research (DataForSEO + SerpAPI fallback, обогащённый парсинг); при падении обоих провайдеров — лог, шаг **`serp_research`** в **`failed`**, исключение; задача падает, но **site project** продолжает со следующей страницей (см. раздел «Проекты: архивация…» ниже)
- [x] Competitor Scraping (Serper.dev + Direct HTTP fallback, ThreadPoolExecutor)
- [x] AI Structure Analysis (JSON response, parsed sub-variables)
- [x] Chunk Cluster Analysis
- [x] Competitor Structure Analysis
- [x] Final Structure Analysis (JSON outline)
- [x] Structure Fact-Checking
- [x] Primary Generation (с exclude words валидацией + retry)
- [x] Primary Generation About / Legal — отдельные агенты **`primary_generation_about`**, **`primary_generation_legal`** для пресетов **`about`** / **`legal`**
- [x] Competitor Comparison
- [x] Reader Opinion
- [x] Interlinking & Citations
- [x] Improver (с exclude words валидацией + retry)
- [x] Final Editing (с force-removal exclude words + SCHEMA cleanup; контекст LLM без числового «таргета» по словам конкурентов — см. раздел **Pipeline: контекст шага `final_editing`** выше)
- [x] Content Fact-Checking (soft/strict modes, JSON report)
- [x] HTML Structure (с site template reference)
- [x] Meta Generation (JSON; часто **`results[]`** с вариантами Title/Description/H1/Trigger — см. раздел **2 апреля 2026**)

### Опциональная Image Generation Цепочка (Midjourney)
- [x] LLM-агент `image_prompt_generation`: извлечение MULTIMEDIA блоков и генерация промпта **по каждому блоку** (с переменными `type`, `description`, `purpose`, `parent_title`, `location`); парсер outline — **мультиязычные ключи**, строка/список вместо dict, встройки в текстовые поля, fallback по сырому JSON-тексту (см. раздел 28 марта 2026 ниже)
- [x] Сервисный шаг `image_generation`: генерация через GoAPI (Midjourney proxy) и хостинг в ImgBB
- [x] Пауза на ревью в UI: `_pipeline_pause.reason === "image_review"`
- [x] Сервисный шаг `image_inject`: вставка одобренных картинок в финальный HTML
- [x] UI `/prompts`: агент отображается как **Image Generation** (ключ в БД остаётся `image_prompt_generation`)

### Pipeline-фичи
- [x] Resume capability — пропуск уже завершённых шагов при retry/resume
- [x] Step results с model/cost/timestamp/resolved_prompts/variables_snapshot; опционально **`input_word_count`**, **`output_word_count`**, при критической потере на `html_structure` — **`word_count_warning`**, **`word_loss_percentage`**
- [x] Rerun отдельного шага с feedback и каскадной инвалидацией
- [x] Rerun image-шагов без каскада инвалидирует только `image_inject` (цепочка возобновляется корректно)
- [x] Test Mode — пауза после primary_generation для ручного одобрения
- [x] Template variables system ({{variable}}) с отчётом о resolved/unresolved/empty
- [x] Critical variables check per-agent
- [x] Exclude Words injection в system prompt + post-generation валидация
- [x] SCHEMA/JSON-LD prohibition в final_editing
- [x] Heartbeat + stale detection (cleanup_stale_tasks каждые 10 минут + step-timeout контроль)
- [x] Excluded domains filtering (social networks, review sites)
- [x] Redis-кэш для `serp_research` (по `keyword+country+language+engine`) с TTL и kill-switch (`SERP_CACHE_ENABLED`)
- [x] Redis-кэш для `competitor_scraping` per-URL с метриками `cache_hits` / `cache_misses`
- [x] Rerun `serp_research` инвалидирует Redis-кэш SERP (fresh fetch при повторном запуске)

### Система проектов
- [x] SiteBlueprint + BlueprintPage модели
- [x] SiteProject с sequential page generation; поле **`is_archived`** (скрытие из основного списка без удаления); миграция Alembic **`e7f8a9b0c1d2_add_is_archived_to_site_projects`**
- [x] Brand seed vs standard keyword templates
- [x] Cooperative cancellation (stop/resume)
- [x] Site builder — ZIP-архив с навигацией
- [x] Дедупликация контента (ProjectContentAnchor)
- [x] **Page-per-task архитектура проектов:** `process_site_project` = стартер, `advance_project` = координатор, `process_project_page` = изолированный Celery-task на одну страницу; при ошибке страницы проект продолжается на следующую, сбои аккумулируются в `error_log` (JSON), финализация вынесена в `finalize_project`

### 31 марта 2026 — Pipeline Observability + Isolated Project Pages

**Backend (`app/workers/tasks.py`, `app/services/pipeline.py`, `app/services/llm.py`, `app/config.py`, `app/workers/celery_app.py`):**
- Проекты переведены на модель **one page = one Celery task**: отдельные задачи `process_project_page` и `advance_project`, плюс `finalize_project`.
- В `SiteProject` добавлено поле **`generation_started_at`** (миграция `h4c5d6e7f9a1_add_generation_started_at_to_site_projects`) — фактический старт генерации.
- LLM-вызовы получили явный timeout через **`LLM_REQUEST_TIMEOUT`**; в логах — время попытки, время ответа/ошибки, retry-информация.
- В пайплайне добавлен `mark_step_running`: для running-шага сохраняется **`started_at`**; `save_step_result` обновляет `last_heartbeat`.
- В `call_agent` расширено промежуточное логирование (отправка запроса, retry sleep, получение ответа с токенами/стоимостью) и предупреждение при слишком большом контексте (`~>50k` токенов).
- Per-step timeout в `run_phase` теперь опирается на **`STEP_TIMEOUT_MINUTES`**.
- Celery получил soft-limit: **`CELERY_SOFT_TIME_LIMIT`**; `cleanup_stale_tasks` запускается каждые 10 минут и дополнительно проверяет зависшие running-шаги по `started_at`.

**Projects API / UI (`app/api/projects.py`, `frontend/src/pages/ProjectDetailPage.tsx`, `frontend/src/api/projects.ts`):**
- В ответы проекта добавлено поле **`generation_started_at`**.
- Добавлен статус **`awaiting_page_approval`** и endpoint **`POST /api/projects/{id}/approve-page`**.
- Поддержан режим **`PROJECT_PAGE_APPROVAL`**: после завершения страницы проект может ждать ручного подтверждения продолжения.
- На `ProjectDetailPage` добавлен блок **Approve & Continue** для `awaiting_page_approval`; расчёт elapsed/ETA использует `generation_started_at ?? started_at`.

**Task UI (`frontend/src/components/tasks/StepCard.tsx`):**
- Для шагов `running` показывается live-таймер `Running... (Xm Ys)`.
- Для `completed` показывается фактическая длительность по `started_at -> timestamp`.
- Добавлен индикатор `⚠ slow` при выполнении шага дольше 5 минут.

### Админ-панель (React SPA)
- [x] Разделы: Дашборд, Проекты, Блупринты (страницы: **Pipeline preset** + optional **custom** шаги), Задачи, Статьи, **Templates** (`/templates`), **Sites** (`/sites`), **Legal Pages** (`/legal-pages`), Авторы, **Prompts** (`/prompts`), Логи, Настройки
- [x] SERP Viewer с таблицами (Organic, PAA, Featured Snippet, KG, AI Overview)
- [x] SERP Export в ZIP с CSV
- [x] Scraping результаты с таблицей ошибок
- [x] Step Monitor с tabs (Result / Промпты / Debug Variables); список шагов на **Task Detail** берётся из **`_pipeline_plan.steps`** или упорядоченно из **`step_results`** (см. раздел **«6 апреля 2026 — Pipeline Presets»**)
- [x] Промпты: агенты пайплайна в т.ч. **`primary_generation_about`**, **`primary_generation_legal`**; переменные reference, skip toggle, test dry-run; Model Settings с **`_*_enabled`**, **`PUT`**, **`syncedPromptIdRef`** (см. раздел **«Model Settings: флаги *_enabled»** выше)
- [x] Задачи: создание, CSV import, next/start-all, **start-selected** (чекбоксы + chain), **force-status** для **`processing`** и **`stale`**, rerun-step
- [x] Task Detail: табы `Pipeline` + `Logs` + опционально `🖼️ Image Review`/`📝 Article Review` (**Article Review**: Monaco Source + iframe Preview, выбор последнего HTML-шага, **`PUT .../step-result`**); отдельная вкладка `Prompts Debug` не используется; **Export DOCX** при завершённой задаче, **`final_editing`** или черновиках **`primary_generation_about` / `primary_generation_legal`**
- [x] Факт-чек viewer с resolve issues
- [x] Статьи: вкладка **Metadata** — полный JSON **`meta_data`** из шага `meta_generation` (если сохранён в БД); иначе fallback на title + description; **Download HTML** / **Export DOCX** с **`GET /api/articles/{id}/download`**; вкладка **html** — единый **Monaco** read-only / edit (**`ArticleDetailPage`**)
- [x] **LlmStepView:** плашка «Words: … → …» и предупреждение при большой потере слов на шаге (данные из `step_results`)
- [x] Проекты: create/stop/resume/download ZIP; **preview** (dry-run; **`use_site_template`**, бейдж **Template: OFF**), **clone** / **start**, **`serp_config`**, **`project_keywords`** (опц.), **`use_site_template`** в create/list/detail/clone, **cluster-keywords**, **export CSV**, **export DOCX**; список с **`progress`**, **`total_cost`**, фильтры **`archived`**, **`status`**, **`search`**; колонки GEO, **Pages**, **Failed**, **Cost**; архив/восстановление; деталка: **`failed_count`**, **`error_log`**, cost/timing/**`log_events`**, **Retry Failed Pages**, **Delete** (не в `generating`/`pending`); **`POST /api/projects`** с **`target_site`**; **409** дубликат с ссылкой на проект (**`formatApiErrorDetail`** + **`existing_project_id`**); toasts (**`formatApiErrorDetail`**, `skipErrorToast`); **`RouteErrorBoundary`**; дашборд — бейдж **SERP health**
- [x] Список проектов с фильтром **`archived`**, архивировать/восстановить — в React (**`ProjectsPage`** / деталка)
- [x] Управление .env из UI
- [x] OpenRouter models autocomplete

### Уведомления
- [x] Telegram: task success, task failed, serper key issue

---

## 🚧 Текущий фокус (v2.0 MVP завершён)

**Статус:** Миграция на React SPA (v2.0) официально завершена и протестирована.

### Март 2026 — страница Prompts («SEO Workflow Optimizer») и API

**Цель:** единая рабочая область для редактирования промптов агентов пайплайна с тестом LLM, переменными и версиями.

**Backend (`app/api/prompts.py`, `app/services/llm.py`, `app/services/pipeline.py`):**
- `GET /api/prompts` — список промптов; `GET /api/prompts/{id}` — полная карточка (system/user, модель, параметры, `skip_in_pipeline`, версия).
- `POST /api/prompts/` — upsert (сохранение черновика, создание новой версии по логике сервиса).
- `POST /api/prompts/test` — тест без привязки к id (если используется).
- `POST /api/prompts/{prompt_id}/test` — тест существующего промпта с подстановкой контекста (JSON переменных); в ответе — вывод LLM, usage/cost при наличии, **`resolved_prompts`** (итоговые system/user после шаблонизации).
- `GET /api/prompts/{id}/versions` — история версий; `POST /api/prompts/{id}/versions/{source_prompt_id}/restore` — восстановить версию (новая активная запись).
- В **`llm.generate_text`** учитываются usage/cost из OpenRouter: приоритет сырой JSON **`usage`** (**`cost`**, cached/reasoning tokens), затем заголовки и оценка — см. раздел **«`llm.py`: стоимость и токены из сырого ответа»** в начале файла.

**Frontend (`frontend/src/pages/PromptsPage.tsx` и связанные):**
- Заголовок страницы: **SEO Workflow Optimizer** (`text-xl font-bold text-slate-900`), над панелью Model Settings.
- **Model Settings:** белая панель (`bg-white`, рамка `slate-200`). Модель через **`ModelSelector`** (список с `GET /api/settings/openrouter-models`). **Max tokens** — чекбокс + число (по умолчанию выключено → `null` в БД; подробности — раздел **«Model Settings (март–апрель 2026)»** ниже и **`max_tokens`** от 28.03.2026). Параметры: чекбокс + **range + number** для **Temperature**; для **Freq. / Pres. / Top P** — чекбокс + **number**. При «выключенном» Temperature в сохранение уходит **`temperature: 1.0`**. Кнопка **Save** в Model Settings; **Test** — в шапке агента. Тест передаёт эффективный **`max_tokens`** в **`POST /api/prompts/{id}/test`**.
- **Skip in pipeline** вынесен из Model Settings в **шапку выбранного агента** (чекбокс рядом с версией / мобильной кнопкой Variables).
- **Сайдбар агентов:** светлый список (белый фон, рамка), выбранный пункт — голубая подсветка (`bg-blue-50`, левая граница). Индикаторы точек: синяя — выбранный агент; серая — `skip_in_pipeline`; зелёная — остальные активные.
- **Редакторы:** только **вертикальный** стек: System Prompt сверху, User Prompt снизу; Monaco **`theme="vs"`** (светлая тема); заголовки секций `bg-slate-50`, без тёмных панелей.
- **Variable Explorer:** поиск, группы переменных; в строке — `{{name}}` и иконка **Copy** (описание в `title`/tooltip, без drag-handle `GripVertical` в списке); drag с строки для вставки в Monaco по-прежнему можно оставить через `draggable`.
- **Тест:** нижняя панель по кнопке Test с вкладками (контекст / результат / resolved prompts); поведение сохранено, стили в общей светлой гамме.
- **Версии:** компактный бейдж `v{N}` с выпадающим списком и **Restore**.
- **Save без отката/перескока:** после `POST /api/prompts/` UI использует ответ `{ id, version }` и переключает `activePromptId` на новый `id` перед инвалидацией кэша. Это убирает визуальный откат на старую версию и fallback на первый агент после обновления списка.

**Layout:** `MainLayout` для `pathname === "/prompts"` не рендерит **`Header`**, main — `bg-slate-100 p-0`, чтобы страница промптов использовала всю высоту под кастомный layout.

**Инструменты:** локальный `npm run build` / `tsc` требуют **Node 18+** (на старых Node, например 12, падает сам TypeScript).

---

### Март–апрель 2026 — обновления (стабильность `html_structure`, промпты, UI)

**Шаг `html_structure` (снижение потери контента, `app/services/pipeline.py`):**
- В **`call_agent`** kwargs для **`generate_text`** собираются через **`llm_sampling_kwargs_from_prompt`**: **`max_tokens`** попадает в запрос только при **`max_tokens_enabled`** и **значении > 0** в строке промпта; в **`llm.generate_text`** ключ добавляется только при **> 0** (иначе максимум модели на стороне OpenRouter). **Актуализация 8.04.2026:** **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** в HTTP-запросе только при соответствующих **`_*_enabled`**.
- При потере слов **> 7%** — один **recovery**-вызов LLM с усиленным контекстом; при **> 20%** после этого — **`programmatic_html_insert`** (`app/services/html_inserter.py`): плейсхолдер `{{content}}` или контейнеры `main` / `article` / `#content` / типичные `div.content` и др.
- **`config`:** `SELF_CHECK_MAX_RETRIES`, `SELF_CHECK_MAX_COST_PER_STEP` — бюджет ретраев для exclude-слов и логика recovery.
- **`call_agent_with_exclude_validation`:** учёт бюджета ретраев по exclude-словам.
- Агент факт-чека контента в пайплайне: **`content_fact_checking`**; в **`get_prompt_obj`** добавлен fallback на устаревшее имя **`fact_checking`** в БД.
- **`scripts/seed_prompts.py`:** для `html_structure` рекомендуется **`google/gemini-2.5-flash`**, **`max_tokens` 16000**, пониженная температура, блок **CRITICAL RULE** про сохранение всего текста; рекомендуемые **`max_tokens`** по остальным агентам в seed; принудительное обновление части промптов через **`PROMPTS_FORCE_UPDATE`**.

**Санитизация промптов и Monaco:**
- **`app/api/prompts.py`:** **`_sanitize()`** — замена U+2028/U+2029, NBSP, BOM при **создании** и **restore** промпта.
- **`scripts/fix_prompt_line_terminators.py`** — одноразовая очистка всех записей в таблице `prompts`.
- **`PromptsPage.tsx`:** Monaco **`unusualLineTerminators: "off"`** на редакторах и панели теста.

**Model Settings (PromptsPage, март–апрель 2026):**
- **Актуализация (апрель 2026, task21):** полное описание — раздел **«Model Settings: флаги *_enabled»** в начале файла (**`_*_enabled`** в БД, **`paramsEnabledFromPrompt`**, **`isPromptDirty`**, **`syncedPromptIdRef`**, **`PUT`** с флагами). Ниже — эволюция до явных флагов.
- **`paramsEnabled`:** `{ maxTokens, temp, freq, pres, top }` — **Max tokens** по умолчанию выключен (в БД **`null`** при отключении); при включении — значение из БД или **4000**.
- Синхронизация с сервером: **`useEffect`** с **`[derivedActiveId, fullPrompt?.id]`** + **`syncedPromptIdRef`** (см. актуальный раздел выше).
- **`saveMutation`:** **`updateInPlace`** / **`PUT`**; при выключенном Max tokens — **`max_tokens: null`**, **`max_tokens_enabled: false`**; **`isPromptDirty`** учитывает все пять тогглов.
- Селектор модели: фиксированная ширина **280px**, **`truncate`** внутри **`ModelSelector`**; ряд параметров с **`flex-wrap`** и фиксированными ширинами блоков (модель 280px, Max tokens 160px, Temperature 180px, Freq./Pres. 160px, Top P 140px).
- Кнопка **Test** убрана из Model Settings; **Test** в шапке карточки агента (рядом с Variables на узком экране). **Save** остаётся в Model Settings.

### Март 2026 — Sites, Blueprints, Projects (формы и API)

**Sites (`SitesPage.tsx`, `app/api/sites.py`):**
- Модалка **Add Site**: поля **Country** и **Language** — `<select>` со списками из уникальных значений **`GET /api/authors`** (как в `TasksPage`), дефолт пустой, placeholder-опции «Select country...» / «Select language...».
- **`DELETE /api/sites/{site_id}`:** если у сайта есть связанные **задачи** (`Task.target_site_id`) или **проекты** (`SiteProject.site_id`), ответ **409** с текстом вида `Cannot delete: site has N tasks and M projects. Delete them first.`; иначе удаляется запись **Site** (глобальные **`templates`** не удаляются). При ошибке удаления в UI в toast показывается **`detail`** из тела ответа API.

**Blueprints (`BlueprintsPage.tsx`, `app/api/blueprints.py`):**
- Таблица блупринтов с **раскрывающейся строкой**; под ней панель **Pages** (lazy `useQuery` → `GET /api/blueprints/{id}/pages`), таблица страниц, **Add Page** / редактирование / удаление, блок **Keyword Preview** (клиентская подстановка `{seed}`).
- После успешного **Create Blueprint** автоматически раскрывается только что созданный блупринт (`setExpandedBlueprintId` по `id` из ответа `POST /api/blueprints`).
- Управление страницами: в т.ч. `DELETE /api/blueprints/{id}/pages/{page_id}` (ответ `{"status": "deleted"}`).

**Projects (`ProjectsPage.tsx`):**
- Модалка **New Project**: **Country** / **Language** — `<select>` из уникальных значений авторов (списки дополняются значениями выбранного **Target Site** и текущего формы, чтобы GEO из сайта всегда было в опциях).
- **Author** — `<select>` авторов, отфильтрованных по выбранным country + language; первая опция **Auto (by country/language)** (`""`); при незаполненном GEO селект задизейблен с единственной опцией **Auto**; при смене country/language сбрасывается `author_id`.
- При выборе **Target Site** предзаполняются **country** и **language** из объекта сайта в кэше `sites`.

### 30 марта 2026 — Projects: `POST` body, `GET` progress, Axios toast, Error Boundary

**Backend (`app/api/projects.py`):**
- **`GET /api/projects`** — в каждом элементе списка поле **`progress`**: 0–100, доля задач проекта со статусом **`completed`**; если задач ещё нет — **0**. Подсчёт одним запросом по **`Task.project_id`** (группировка в Python), без N+1.

**Frontend — создание проекта (`ProjectsPage.tsx`, `frontend/src/api/projects.ts`):**
- Тело **`POST /api/projects`** соответствует **`SiteProjectCreate`**: поле **`target_site`** (UUID выбранного сайта или домен/имя для резолва на бэкенде). Форма UI хранит выбор в **`site_id`**; при сабмите отправляется **`target_site: formData.site_id`**, без поля **`site_id`** (раньше уходило **`site_id`** → **422**). Тип **`SiteProjectCreatePayload`**; **`author_id`** — число или поле не передаётся.
- **`projectsApi.create`** вызывается с **`skipErrorToast: true`** в конфиге Axios, чтобы response interceptor не показывал второй toast; ошибка обрабатывается в **`onError`** мутации через **`formatApiErrorDetail`**.

**Axios (`frontend/src/api/client.ts`, `frontend/src/lib/apiErrorMessage.ts`):**
- В **`toast.error`** попадает только **строка**. Для **`response.data.detail`** используется **`formatApiErrorDetail`**: строка как есть; массив ошибок валидации FastAPI — склейка полей **`msg`**; иначе **`JSON.stringify`**. Это устраняет **React error #31** (объект/массив как React child), в т.ч. при глобальном interceptor.
- Расширение типов: **`frontend/src/types/axios-augment.d.ts`** — флаг **`skipErrorToast`** в **`AxiosRequestConfig`**.

**Error Boundary (`frontend/src/App.tsx`, `frontend/src/components/common/RouteErrorBoundary.tsx`):**
- Маршруты обёрнуты в **`RouteErrorBoundary`** — ошибка рендера в дочернем экране не обнуляет всё приложение (белый экран).

### 30 марта 2026 — Проекты: архивация, устойчивость к сбоям SERP, расширение API и UI

**Модель и миграция**
- **`SiteProject.is_archived`** (Boolean, default false). Миграция: **`alembic/versions/e7f8a9b0c1d2_add_is_archived_to_site_projects.py`**.

**API (`app/api/projects.py`)**
- **`GET /api/projects`**: query **`archived`** (по умолчанию только неархивные), **`status`**, **`search`** (имя, `ilike`); в каждом элементе: **`is_archived`**, **`country`**, **`language`**, **`total_tasks`**, **`completed_tasks`**, **`failed_tasks`**, **`progress`**.
- **`GET /api/projects/{id}`**: **`failed_count`**, **`is_archived`**, **`progress`**, **`error_log`**.
- **`POST /api/projects/{id}/archive`**, **`POST /api/projects/{id}/unarchive`** — без ограничения по статусу проекта.
- **`DELETE /api/projects/{id}`** — удаление проекта и связанных **Task**; запрещено при статусе **`generating`** или **`pending`**.
- **`POST /api/projects/{id}/retry-failed`** — задачи со статусом **`failed`** → **`pending`**, повторная постановка **`process_site_project`** в очередь.

**Pipeline (`app/services/pipeline.py`)**
- **`phase_serp`**: вызов **`fetch_serp_data`** в **try/except**; при ошибке — лог, **`save_step_result`** для **`serp_research`** со **`status="failed"`**, **`raise`** (задача завершается как failed).

**Worker (`app/workers/tasks.py`, `process_site_project`)**
- Ошибка страницы не переводит весь проект в **`failed`**: накопление **`failed_pages`**, **`continue`** к следующей странице; после обхода всех страниц — **`build_site`**, **`project.status = "completed"`**, **`error_log`** = JSON массива сбоев или **`None`**; при **Stop** сохраняется накопленный **`error_log`**.

**React**
- **`frontend/src/pages/ProjectsPage.tsx`**: переключатель **Active / Archived**, фильтр статуса, поиск по имени; колонки **Country/Lang**, **Pages**, **Failed**; иконки **Archive** / **ArchiveRestore**.
- **`frontend/src/pages/ProjectDetailPage.tsx`**: **Retry Failed Pages**, **Delete** (confirm), счётчик failed, блоки ошибок (красный для **`failed`**, янтарный для **`completed`** + **`error_log`** — частичные сбои страниц).
- **`frontend/src/api/projects.ts`**: **`archiveProject`**, **`unarchiveProject`**, **`deleteProject`**, **`retryFailedPages`**, расширенный **`getAll`**.

---

### Март 2026 — Проекты: preview (dry-run), SERP-конфиг, CSV, health-check SERP

**Цель:** планировать запуск без записи в БД, задавать SERP на уровне проекта, выгружать отчёты и видеть состояние SERP API до старта.

**Backend (`app/api/projects.py`, `app/services/serp.py`, `app/api/health.py`, `app/models/project.py`)**

- **`POST /api/projects/preview`** — регистрируется **перед** `POST /api/projects/`, чтобы путь не перехватывался как `{id}`. Тело: как создание проекта без обязательного `name` (см. **`ProjectPreviewRequest`**): blueprint, seed, GEO, `target_site`, опционально **`author_id`**, **`serp_config`**. Резолв сайта **без автосоздания** (если сайт не найден — в ответе `site.will_be_created`, предупреждение в **`warnings`**). Автор: manual / auto / none. Проверка наличия **HTML-шаблона** у сайта: **`site.template_id`** и активная запись **`Template`**. Страницы блупринта с итоговыми keyword и **standard/brand** шаблоном. **Оценка стоимости:** средняя по последним **50** завершённым задачам с `total_cost > 0`, умноженная на число страниц; при отсутствии данных — `null`. В ответе: **`serp_health`** (`get_serp_health()`), дополнительные **`warnings`** при `overall != ok` для SERP.
- **`SiteProject.serp_config`** (JSONB): ключи `search_engine`, `depth`, `device`, `os` — валидация при **`POST /api/projects`**. Сохраняется в проект; при создании задач в **`process_site_project`** в **`Task.serp_config`** подставляется конфиг проекта. В **`GET /api/projects`** и **`GET /api/projects/{id}`** поле **`serp_config`** в ответе. Клонирование копирует **`serp_config`** с исходного проекта.
- **`POST /api/projects`** — в ответе опционально **`serp_warning`** (мягкая проверка `get_serp_health()` после постановки в очередь; создание не блокируется).
- **`GET /api/projects/{id}/export-csv`** — CSV по задачам проекта (колонки: page_slug, keyword, page_type, status, filename, title, description, word_count, cost, fact_check, created_at), пакетная загрузка **`GeneratedArticle`** и **`BlueprintPage`**, строка **TOTAL** в конце.
- **`GET /api/health/serp`** — обёртка над **`get_serp_health()`** в `serp.py`: тестовые вызовы DataForSEO и SerpAPI, поля **`overall`**, **`_from_cache`**, TTL **5 минут**, параметр **`?force=true`** для сброса кэша.

**Frontend (`ProjectsPage.tsx`, `ProjectDetailPage.tsx`, `DashboardPage.tsx`, `frontend/src/api/projects.ts`, `frontend/src/api/dashboard.ts`)**

- Модалка создания проекта: кнопка **Preview** (иконка Eye), блок превью (карточки, таблица страниц, warnings), секция **Advanced SERP Settings** (engine, depth, device, os); при создании — toast с **`serp_warning`** при наличии.
- Список проектов: колонка **Cost**; деталка: **`Export Summary (CSV)`** (blob, авторизация через axios), бейджи нестандартного **serp_config** в шапке.
- **Dashboard:** бейдж состояния SERP (online / degraded / not configured), опрос раз в **5 минут**.

- **`POST /api/projects/{id}/clone`** — копия проекта в статусе **`pending`** (новые задачи, без статей); опционально переопределить имя, seed, GEO, сайт, автора; **`serp_config`** копируется с исходника.
- **`POST /api/projects/{id}/start`** — только для статуса **`pending`**: постановка **`process_site_project`** в очередь (проверка worker **503** при недоступности). Дубликат здесь **не** проверяется; **409** с **`existing_project_id`** — при **`POST /api/projects`** и **`POST .../clone`**, если уже есть неархивный проект с тем же **blueprint + seed + site** и статусом не **`failed`**.
- **`GET /api/projects`** / **`GET /api/projects/{id}`** — агрегаты **`total_cost`**, **`started_at`**, **`completed_at`**, **`duration_seconds`**, **`avg_cost_per_page`**, **`avg_seconds_per_page`**, **`remaining_pages`**, **`log_events`** (массив записей проекта); в списке — **`total_cost`** по сумме задач.
- **`app/services/serp.py`:** при ошибке обоих провайдеров SERP — **retry** с экспоненциальной задержкой (по умолчанию Google organic path).

**Миграции Alembic**

- **`f1a2b3c4d5e7_add_project_timings_and_logs.py`** — **`started_at`**, **`completed_at`**, колонка **`logs`** у **`site_projects`** (переименована в **`log_events`**, миграция **`t7u8v9w0x1yb`**).
- **`g2b3c4d5e6f8_add_serp_config_to_site_projects.py`** — **`serp_config`** у **`site_projects`**; см. также **`c8f9a0b1d2e3_add_serp_config_to_tasks.py`** — **`serp_config`** у **`tasks`**.

---

### Март 2026 — Задачи (Tasks), деталь задачи, шаги pipeline (StepCard)

**Цель:** выборочный запуск задач, человекочитаемые шаги SERP/Scraping, табы результата/промптов/переменных для LLM-шагов, рабочие execution logs, без дублирующих табов.

**Backend (`app/api/tasks.py`):**
- `POST /api/tasks/start-selected` — тело `{ "task_ids": ["uuid", ...] }`; выбираются только задачи со статусом **`pending`** и **`project_id is null`**; порядок как у очереди (`priority` DESC, `created_at` ASC); запуск через Celery **`chain`** (последовательно). Невалидные UUID в списке пропускаются.
- `GET /api/tasks/{id}` — в ответ добавлены **`country`**, **`language`** (для карточки справа на деталке задачи).
- `DELETE /api/tasks/{id}/cache` — ручная инвалидация SERP-кэша для задачи.

**Frontend — `TasksPage.tsx`:**
- Первая колонка таблицы: чекбоксы только для **`pending`**; в заголовке — **Select all** по видимым pending-задачам (с `indeterminate`).
- Состояние выбора: `useState<Set<string>>`.
- Кнопка **Start Selected (N)** рядом с Start Next / Start All; вызывает `tasksApi.startSelected`.

**Frontend — `TaskDetailPage.tsx`:**
- Два таба: **Pipeline Execution** и **Execution Logs** (убраны отдельные табы SERP Data и Prompts Debug — детали в шагах pipeline).
- Логи: поля из `add_log` — **`ts`**, **`msg`**, **`level`**, **`step`** (без `timestamp`/`message`).

### Март 2026 — Image pipeline (актуализация)

- Для выполнения image-цепочки должны быть заданы: `IMAGE_GEN_ENABLED=true`, `GOAPI_API_KEY`, `IMGBB_API_KEY`.
- Если `IMAGE_GEN_ENABLED=false`, шаги `image_prompt_generation`/`image_generation` будут корректно скипаться с логами `disabled`.
- Изменения `.env` применяются после перезапуска контейнеров `web`/`worker`.

### Март 2026 — SERP/Scraping cache (актуализация)

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

### 28 марта 2026 — статьи: `meta_data`, контроль слов по шагам

**Актуализация (2.04.2026):** если JSON от `meta_generation` имеет вид **`{"results": [...]}`**, поля **`title`/`description` статьи** заполняются из **первого варианта** (ключи `Title`/`Description` или `title`/`description`); см. раздел **«2 апреля 2026»** выше.

**Backend**
- Модель **`GeneratedArticle`**: колонка **`meta_data`** (JSONB) — полный распарсенный ответ агента `meta_generation`; заполняется при сборке статьи в конце `run_pipeline`. Миграция Alembic: `d1e2f3a4b5c6_add_meta_data_to_generated_articles`.
- **`GET /api/articles/{id}`** возвращает **`meta_data`**.
- **`app/services/word_counter.py`**: **`count_content_words()`** — слова видимого текста (HTML через BeautifulSoup, без тегов).
- **`save_step_result`** принимает опционально **`input_word_count`**, **`output_word_count`**, **`word_count_warning`**, **`word_loss_percentage`**.
- Подсчёт слов и запись в шаг: **`primary_generation`** (output), **`improver`**, **`final_editing`**, **`html_structure`** (при потере **> 7%** слов контента — `add_log` warn + флаги в step_data), **`image_inject`**.
- **`word_count` статьи** считается через **`count_content_words`** по финальному HTML контента.

**Frontend**
- Тип **`Article`**: поле **`meta_data`**.
- **`ArticleDetailPage`**, вкладка **metadata**: если **`meta_data`** непустой объект — все ключи JSON отдельными блоками (для `title` / `description` сохранены подсказки по длине); иначе прежний вид.
- **`LlmStepView`**: строка **`📊 Words: …`** при наличии счётчиков; красный алерт при **`word_count_warning`**; цвет строки по диапазонам потери (зелёный / янтарный / красный).

---

### 28 марта 2026 — парсер MULTIMEDIA для image pipeline (`image_utils.py`)

**Проблема:** outline на языке статьи даёт ключи вроде `МУЛЬТИМЕДИА`, `MULTIMÉDIA`, `medien` и т.д.; раньше искалось только английское `MULTIMEDIA`.

**Реализовано**
- Набор **`MULTIMEDIA_KEY_VARIANTS`** и **`_is_multimedia_key()`** — мультиязычные и альтернативные ключи (`image_description`, `visual`, `изображение`, …), префиксы с номером (`multimedia_5`, `мультимедиа_4`, …).
- Значение multimedia-ключа: **dict** (как раньше), **строка** (>10 символов) → разбор через **`_parse_multimedia_from_text`**, **список** dict/строк → несколько блоков.
- Сканирование **длинных строковых** полей dict (**> 30** символов) на встройки: скобки `[MULTIMEDIA: …]`, жирный markdown, тире после тега, типовые `[Image: …]` / `[Инфографика: …]` — функции **`_extract_multimedia_from_text_content`**, regex по тегам EN/RU/FR/DE/ES/IT/PL.
- **`phase_image_prompt_gen`**: если **`extract_multimedia_blocks(outline_json)`** вернул пусто, а сырой результат final structure **> 100** символов — повторный поиск через **`_extract_multimedia_from_text_content(outline_raw, "outline_raw")`** + лог `info`; если блоков нет — лог **`[DEBUG]`** с первыми 1500 символами outline + прежние предупреждения.
- Тесты: **`tests/test_image_utils.py`** (в т.ч. русский/французский ключ и текст, строка, список, смешанные языки).

---

### 28 марта 2026 — `max_tokens` в LLM (OpenRouter)

**Проблема:** лимит вывода из поля **`prompts.max_tokens`** в БД не передавался в Chat Completions — провайдер использовал дефолт модели.

**Backend**
- **`app/services/llm.generate_text`**: опциональный аргумент **`max_tokens: Optional[int] = None`**; в **`client.chat.completions.create`** ключ **`max_tokens`** добавляется **только если значение не `None` и > 0** (ноль не отправляется).
- **`call_agent`** (`pipeline.py`): сборка kwargs через **`llm_sampling_kwargs_from_prompt`** — **`max_tokens`** только при **`max_tokens_enabled`** и **> 0** в записи промпта (апрель 2026).
- **`app/api/prompts.py`**: модель **`PromptTest`** — поле **`max_tokens`**; **`POST /api/prompts/test`** передаёт его в **`generate_text`**. **`PromptTestContext`** расширен overrides (в т.ч. **`max_tokens_enabled`**, **`max_tokens`**) для теста из UI без Save.

**Frontend (`PromptsPage.tsx`)**
- Панель **Model Settings**: тоггл **Max tokens**; при сохранении через **`PUT`** — **`max_tokens: null`** и **`max_tokens_enabled: false`**, если выключено (см. раздел **«Model Settings: флаги *_enabled»**).
- **Run Agent:** в **`POST /api/prompts/{id}/test`** уходят актуальные **`llm`**-поля из **`PromptTestPanel`** (включая флаги и лимит).

**Ориентиры по агентам** (настраиваются в UI, не захардкожены): `meta_generation` ~1000; аналитические структуры ~4000–8000; `primary_generation`, `improver`, `final_editing` ~16000; прочие LLM-шаги ~4000–8000.

---

**Что было сделано в последнем спринте (исторически):**
- Полностью переписан UI с использованием React, Vite, Tailwind и TanStack Query.
- Реализованы 10 вкладок управления бизнесом (Dashboard, Проекты, Задачи, Промпты, Логи и др.).
- Интегрирован real-time polling статусов задач (TanStack Query).
- Добавлена поддержка Sequential Mode для строгой очереди задач.
- Реализован SERP Data Viewer с таблицами и выгрузкой ZIP/CSV.
- Установлено управление `.env` файлом напрямую из UI SettingsPage с API.
- Встроен просмотр логов и мониторинг шагов Celery (LogsPage + StepMonitor).

**Недавние исправления (Hotfixes):**
- **Prompts (апрель 2026, task21):** булевы **`_*_enabled`** в БД и API; **`prompt_llm_kwargs`** в pipeline и тесте; UI на серверных флагах; **`syncedPromptIdRef`** для гидратации — см. раздел **«Model Settings: флаги *_enabled»** выше. **8.04.2026:** отключённые **freq/pres/top_p** не уходят в OpenRouter; см. раздел **«8 апреля 2026 — LLM…»**.
- **Prompts (3.04.2026):** **`PUT /api/prompts/{id}`** для сохранения без новой версии; стабильная гидратация по **`fullPrompt?.id`**; портал + fixed для **`ModelSelector`**; защита **`setEditState`** от **`null`** — см. раздел **3 апреля 2026** выше.
- **meta_generation + `results[]` (2.04.2026):** корректное извлечение Title/Description для `GeneratedArticle` при формате с массивом вариантов — см. раздел **2 апреля 2026**; **актуализация:** одиночный DOCX — **H1** в шапке, **Title** в мета-таблице через **`_get_all_meta_from_task`** — см. раздел **«DOCX одиночной статьи: шапка H1»** выше.
- **Tasks Form:** Восстановлена полная форма создания задачи (поля `author_id`, `additional_keywords`, `priority`).
- **Prompts UI:** Устранено дублирование (фильтр `active_only=True` на бэкенде), добавлены User-Friendly имена агентов.
- **Prompt Testing:** Синхронизировано изолированное тестирование, добавлен Backend-эндпоинт для инъекции JSON-переменных при тесте существующих промптов.
- **Task Detail / StepCard:** Промпты и переменные по шагам внутри раскрытой карточки шага (`LlmStepView`), а не отдельной вкладкой «Prompts Debug» (таб убран в пользу pipeline).
- **Article Review / Article HTML (апрель 2026):** **`PUT /api/tasks/{id}/step-result`**, Monaco на **Article Review** и единый Monaco на вкладке **html** статьи — см. раздел **«Monaco для HTML: Article Review, Article Detail»** выше.
- **Variables UI:** На странице Prompts добавлена удобная выпадающая панель со всеми (40+) переменными, разбитыми на 4 логические группы (задачи, автор, SERP, результаты). Добавлен "живой" поиск по переменным. `main_keyword` везде заменена на `keyword`.
**Что происходит сейчас:**
- Система стабильно работает в production.
- Формируется backlog для более глубоких серверных фичей (Q2 2026).
---

## 📋 Следующие задачи

**Приоритет 1 (критично — стабильность):**
1. Quality Gate — автовалидация вывода каждого LLM-шага (min length, HTML tags, JSON validity)
2. Fallback-модель — при сбое основной модели автоматически переключаться на резервную
3. Dead Letter Queue улучшение — retry from last step для stale задач

**Приоритет 2 (важно — функциональность):**
1. Target Word Count — явное указание длины статьи (поле в Task)
2. WordPress auto-publish (REST API integration)
3. Аналитика стоимости (breakdown по моделям, шагам, графики в дашборде)
4. Параллельные шаги анализа (ThreadPoolExecutor для 3 аналитических агентов)

**Приоритет 3 (UX / nice-to-have):**
1. WYSIWYG-редактор статей в UI
2. Превью статьи в iframe
3. Bulk-операции в UI (массовый delete/retry/export)
4. Клонирование задач и промптов
5. A/B сравнение версий промптов

**Приоритет 4 (будущие возможности):**
1. Генерация изображений (DALL-E / SD)
2. Планировщик генерации (cron-based)
3. Мультиязычная генерация (parent_task_id)
4. Экспорт в Google Docs / Sheets
5. Rate Limiter для LLM-вызовов (Redis-based)
6. Webhook / Callback API

---

## 🐛 Известные проблемы

- [ ] Pipeline не валидирует вывод LLM — мусор или обрезанный ответ передаётся дальше (→ Quality Gate)
- [ ] При падении модели весь пайплайн падает — нет fallback на другую модель
- [ ] Settings API пишет напрямую в .env — требует ручного рестарта контейнеров для применения
- [x] ~~Нет endpoint для правки статей~~ — реализовано **`PATCH /api/articles/{id}`** + UI на **`ArticleDetailPage`** (апрель 2026)
- [ ] Alembic миграции содержат pass в некоторых upgrade/downgrade (пустые миграции)
- [ ] cost tracking может быть неточным — если в сыром JSON нет **`usage.cost`** и нет **`x-openrouter-cost`**, используется грубая оценка по токенам (см. раздел **«`llm.py`: стоимость и токены из сырого ответа»** выше)

---

## 💡 Идеи для улучшения

- RAG-интеграция через Supabase pgvector (уже есть инфраструктура, не подключено к pipeline)
- Метрики качества статей (readability, keyword density, heading count)
- Кеширование SERP-данных для повторных запросов по тому же ключу
- Batch processing через Celery groups вместо chain для независимых задач