# ИЗВЕСТНЫЕ БАГИ

**Дата последнего обновления:** апрель 2026 (**task55**: exclude-words retry оставлен только в `final_editing`, upstream-шаги без повторных exclude-ретраев; **task54**: NUL-санитизация scraped/SERP данных и обработка OpenRouter 402 с adaptive `max_tokens`/`InsufficientCreditsError`; ранее **task53 E**, **task52**, **task50**, **task48**, **task47**, **taskco**, **task41**, **task40** — см. **`CURRENT_STATUS.md`**)

---

## ✅ Исправлено в task55 (24.04.2026)

### Лишние дорогие exclude-words ретраи в upstream-шагах
**Было:** `call_agent_with_exclude_validation` вызывался не только в `final_editing`, но и в `primary_generation`, `primary_generation_about`, `improver`, `primary_generation_legal`, что провоцировало парные длинные LLM-вызовы и рост стоимости.  
**Сделано:** в `app/services/pipeline/steps/draft_step.py` и `app/services/pipeline/steps/legal_step.py` upstream-шаги переведены на `call_agent`; `final_editing` не изменён (там остаются retry + `remove_violations()` как финальный гарант).

---

## ✅ Исправлено в task54 (24.04.2026)

### NUL-байты из scraping/SERP ломали commit в Postgres
**Было:** отдельные страницы падали на `ValueError: A string literal cannot contain NUL (0x00)` при записи `competitors_text` / JSONB payloads.  
**Сделано:** добавлен `app/utils/text_sanitize.py` (`strip_nul`) и применён на ingress в `app/services/scraper.py` и `app/services/pipeline/steps/serp_step.py` перед записью в БД.

### OpenRouter 402 с oversized `max_tokens` ретраился без шансов на успех
**Было:** при ошибке `402 ... can only afford N` retry-loop повторял тот же oversized запрос с задержкой.  
**Сделано:** в `app/services/llm.py` добавлена обработка 402: downscale `max_tokens` по affordance и немедленный retry без sleep; при неразрешимом кейсе — fail-fast через `InsufficientCreditsError` (`app/services/pipeline/errors.py`), без бессмысленных повторов.

---

## ✅ Исправлено в task53 E (23.04.2026)

### Страница проекта: обрезанный лог, возможный `statement_timeout` на `UPDATE step_results`
**Было:** в лог проекта попадали только **~200** символов **`str(exception)`** без traceback; серверный **`statement_timeout=60000`** мс на всех соединениях ORM мог обрывать долгие **`UPDATE`** с большим **`step_results`**; любая ошибка пайплайна продвигала **`current_page_index`** как при «провале страницы», в т.ч. при временных сбоях БД.
**Сделано:** **`statement_timeout=600000`** мс в **`app/database.py`**; в **`process_project_page`** — **`traceback`** в **`Task.error_log`** (хвост до 8000 символов), строка **FAILED** в **`project.log_events`** с первой строкой ошибки и **`task_id`**; отдельная ветка **`OperationalError`/`DBAPIError`**: **`rollback`**, задача и проект в **`pending`**, **`advance_project.apply_async(..., countdown=60)`** без пропуска страницы. Подробности — **`docs/CURRENT_STATUS.md`**, раздел **«task53 E»**, план **`task53.md`** (раздел **E**).

---

## ✅ Исправлено в task52 (22.04.2026)

### Долгий LLM-шаг, `stale` в Beat и продолжающийся worker
**Было:** **`LLM_REQUEST_TIMEOUT=300`** и **`max_retries=3`** давали до ~16+ минут на один вызов; **`STEP_TIMEOUT_MINUTES=15`** мог быть меньше; SIGALRM в Celery worker не прерывал шаг в worker-thread; после **`stale`** или force-fail HTTP к OpenRouter продолжался.
**Сделано:** дефолтные **`LLM_REQUEST_TIMEOUT=600`**, **`STEP_TIMEOUT_MINUTES=30`**, **`max_retries=2`**, короткий backoff на gateway/timeout; опционально **`LLM_MODEL_TIMEOUTS`** / **`LLM_MODEL_FALLBACKS`**; **`_call_with_timeout`** через **`ThreadPoolExecutor`** + **`step_deadline`** для exclude-retry; колонка **`tasks.celery_task_id`**, revoke в **`cleanup_stale_tasks`** и при **`POST /api/tasks/{id}/force-status`** (**`fail`**). Подробности — **`CURRENT_STATUS.md`**, раздел **«task52»**, план **`task52.md`**.

---

## ✅ Исправлено в taskco §5 (22.04.2026)

### NameError в `preview_project` при markup-only режиме
**Было:** в `app/api/projects.py` → `preview_project()` переменная `warnings` использовалась до инициализации: при вызове `warnings.append(...)` до первого присвоения возникал `NameError: name 'warnings' is not defined`.
**Исправлено:** добавлена явная инициализация `warnings: List[str] = []` в начало функции. Баг воспроизводился при markup-only preview (без `target_site`) в определённых сочетаниях параметров.

### Голые `except:` → `except Exception:` (E722)
**Было:** несколько мест в `app/services/scraper.py`, `app/services/serp.py` и других использовали `except:` без типа — перехватывало `BaseException`, в т.ч. `KeyboardInterrupt`/`SystemExit`.
**Исправлено:** все 39 ручных правок в рамках ruff-cleanup (taskco §5): `except:` → `except Exception:`.

### `== None` / `== True` сравнения (E711/E712)
**Было:** в `app/api/` и `app/services/` встречались `x == None`, `x != None`, `x == True` — неидиоматичные сравнения, могущие давать ложные срабатывания при переопределённом `__eq__`.
**Исправлено:** заменены на `.is_(None)` / `is None` / `is True` в SQLAlchemy-контексте и в общем Python-коде.

---

## ✅ Недавно снятые UX-проблемы (без отдельного BUG-id)

### Потеря meta-тегов на non-main страницах проекта
**Было:** если `generate_full_page()` возвращал `None` (шаблон отключён у проекта / нет активного template у сайта), `site_builder` брал fallback `article.html_content`, и часть страниц попадала в экспорт без `<head>` с корректными `<title>` и `<meta name="description">`.  
**Сделано (20.04.2026, task40):** добавлен `ensure_head_meta()` в `app/services/template_engine.py`; в `pipeline` финальный HTML всегда проходит через эту функцию независимо от результата шаблона. Для фрагментов выполняется минимальная HTML-обёртка с `<head>`, для full-page — update/insert meta внутри существующего `<head>`. В `site_builder` добавлен warning при fallback на `html_content`.

### В финальном HTML отсутствовал блок «Об авторе»
**Было:** данные автора использовались в контексте LLM, но не попадали в итоговый документ для публикации/экспорта.  
**Сделано (20.04.2026, task40):** добавлен `render_author_footer()` и инъекция блока `<section class="author-info">` в конец `<body>` на этапе сборки `GeneratedArticle.full_page_html` (single task + project pages). Также добавлено поле `authors.country_full` (миграция `u8v9w0x1y2zc`, API, UI AuthorsPage).

### Обязательный Target Site при создании проекта (нужна только разметка)
**Было:** поле **Target Site** было обязательным на фронте и в схеме API; **`site_id` NOT NULL** в БД не позволял создать проект без сайта, хотя **`use_site_template=false`** уже отключал обёртку.  
**Сделано (20.04.2026):** чекбокс **Markup only** в **`ProjectsPage`**, опциональный **`target_site`** в **`POST /api/projects`** и **`POST /api/projects/preview`**, резервный сайт **`__markup_only__`** и **`_resolve_site_or_markup_only`** в **`app/api/projects.py`**. Подробности — **`CURRENT_STATUS.md`**, **«20 апреля 2026 — Markup only»**.

### Чекбокс Use site HTML template (видимость и шаблон)
**Было:** чекбокс не появлялся, если в ответе **`GET /api/sites`** не было **`template_id`** / устарел кэш; при смешанном регистре языка — отдельная история (см. ниже).  
**Сделано:** в **`_site_out`** — **`has_template`**, **`template_id`**, **`template_name`**; **`refetchOnMount`**, **`sitesApi.getOne`**, **`siteHasTemplate`**; блок с чекбоксом рендерится при **`formData.site_id`**; без шаблона у сайта — **`disabled`** и текст *«No HTML template assigned…»*; **`onSiteChange`** выставляет **`use_site_template`** по наличию шаблона; **`useEffect`** сбрасывает **`use_site_template`**, если шаблона нет; тесты **`tests/test_sites_api.py`**. Если в браузере «старое» при свежем образе — порт **`3001`** по умолчанию, **`build --no-cache frontend`**, жёсткий refresh. Подробности — **`CURRENT_STATUS.md`**, **18.04.2026**, раздел про Sites API и Docker в том же разделе.

### Дубликаты языка в дропдауне (French / french)
**Было:** **`Set`** по строкам case-sensitive и фильтр авторов по **`===`** давали дубли и пустой список авторов.  
**Сделано:** миграция **`s6t7u8v9w0xe`**, **`normalize_language`** в **`authors`/`sites` API**, **`languageDisplay.ts`** + правки **ProjectsPage** / **TasksPage** / **SitesPage**; **`tests/test_language_normalize.py`**. Подробности — **`CURRENT_STATUS.md`**, **18.04.2026**, раздел про Language.

---

## 🔴 Критичные (влияют на стабильность production)

### BUG-001: Pipeline не валидирует вывод LLM (нет Quality Gate)
**Описание:** Если LLM вернул пустой ответ, обрезанный текст, мусор или невалидный JSON — pipeline передаёт это на следующий шаг без проверки. В результате downstream-шаги получают невалидный контент, и финальная статья может быть бракованной. *(Частичное смягчение для шага **`html_structure`**: лимит токенов, recovery, программная вставка — см. `docs/CURRENT_STATUS.md`; полноценный Quality Gate по-прежнему в планах.)* **Операционно (19.04.2026):** зависший проект в **`pending`**/**`generating`** можно снять через **`POST /projects/{id}/reset-status`** или удалить через **`DELETE ...?force=true`** / массово **`delete-selected`** с **`force`** — см. **`CURRENT_STATUS.md`**. **Операционно (22.04.2026, task52):** разумные таймауты LLM/шага, лимит exclude-retry по **`step_deadline`**, revoke Celery при **`stale`** и force-fail задачи — см. раздел **«task52»** в **`CURRENT_STATUS.md`**.
**Где:** `app/services/pipeline.py` — все `phase_*` функции, `call_agent`
**Воспроизведение:** Поставить модель с маленьким max_tokens (напр. 100) → primary_generation вернёт обрезанный HTML → improver получит мусор → статья сохранится с битым контентом
**Ожидаемое поведение:** Автоматический retry шага при обнаружении невалидного вывода (min length, HTML tags check, JSON validity)
**Приоритет:** P0 — первый в очереди на исправление
**Связано с:** План_развития_проекта → 1.1 Quality Gate

### BUG-002: Нет fallback-модели при сбое основной
**Описание:** `generate_text()` повторяет запросы с одним и тем же **`model`** (до **2** попыток после **task52**). Если провайдер OpenRouter для этой модели отдаёт 5xx — после исчерпания retry задача падает. *(Частичное смягчение **task52**: при заданной строке **`LLM_MODEL_FALLBACKS`** в **`extra_body`** уходит массив **`models`** для provider routing на стороне OpenRouter; в лог пайплайна добавляется строка при **`response.model` ≠ запрошенной**.)* Полноценное «**`fallback_model`** в записи Prompt / **`GLOBAL_FALLBACK_MODEL`**» в конфиге — в планах (**`Roadmap.md`**).
**Где:** `app/services/llm.py` → `generate_text()`
**Воспроизведение:** Указать несуществующую модель в промпте → retry → failed
**Ожидаемое поведение:** После исчерпания retry на основной модели — автоматически переключиться на `fallback_model` из промпта или `GLOBAL_FALLBACK_MODEL` из config
**Приоритет:** P0 (частично снято маршрутизацией OpenRouter через env, см. выше)
**Связано с:** План_развития_проекта → 4.1 Fallback-модель

### BUG-003: Пустые Alembic миграции (pass в upgrade/downgrade)
**Описание:** Миграции `09ae73aad6bf` (Add total_cost) и `bc88319cbdae` (remove style_prompt) содержат `pass` в upgrade и downgrade — операции не выполняются. Вероятно, колонки были добавлены вручную в Supabase, а autogenerate не подхватил разницу.
**Где:** `alembic/versions/09ae73aad6bf_add_total_cost_to_task.py`, `alembic/versions/bc88319cbdae_remove_style_prompt_from_authors.py`
**Воспроизведение:** `alembic upgrade head` на чистой БД — поля total_cost и exclude_words не создадутся (total_cost создаётся в следующей миграции d4fbd61cf552, но bc88319cbdae всё равно пустая)
**Ожидаемое поведение:** Миграции должны содержать реальные операции или быть удалены/объединены
**Приоритет:** P1

### ~~BUG-019: `retryable_errors=(LLMError,)` не работает для LLM-шагов (dead policy)~~ ✅ ИСПРАВЛЕНО (task48)
**Описание:** в большинстве step-классов (`outline/draft/html/meta/legal/final_editing`) указаны policy вида `retryable_errors=(LLMError,)`, но в текущем call-path `LLMError` фактически не бросается: `llm_client` отдаёт/пробрасывает raw исключения (`Exception`, `ValueError`, provider/http errors). В итоге runner не попадает в ветку retry по policy, и шаги падают без ожидаемого retry.
**Где:** `app/services/pipeline/steps/*.py` (policy) + `app/services/pipeline/llm_client.py` (exception mapping).
**Источник:** аудит task47 (`task46-audit.md`, разделы B/C/D).
**Воспроизведение:** вызвать transient ошибку провайдера на любом LLM-шаге с `retryable_errors=(LLMError,)` — retry policy не срабатывает.
**Исправление (апрель 2026, task48):** `app/services/pipeline/llm_client.py` оборачивает provider-вызовы `generate_text` и отсутствие активного prompt в `LLMError` (`raise ... from e`), благодаря чему `StepPolicy.retryable_errors=(LLMError, ...)` реально применяется в runner; дополнительно для optional fact-check шагов включён `skip_on=(LLMError, ParseError)`. Регрессии покрыты `tests/services/test_pipeline_errors.py`.

---

## 🟡 Средние (влияют на UX или точность данных)

### ~~BUG-018: Внутренний 500 как `text/plain` → axios «Network Error»~~ ✅ СМЯГЧЕНО (апрель 2026)
**Описание (исторически):** при необработанном исключении Uvicorn/FastAPI могли отдать тело **`Internal Server Error`** как **`text/plain`**; axios не парсил **`detail`**, пользователь видел общий «Network Error».
**Изменение:** глобальный обработчик в **`app/main.py`** возвращает **`JSONResponse` 500** с **`detail`**, **`path`**, **`method`**; логируется полный traceback. См. **`docs/CURRENT_STATUS.md`**, **16 апреля 2026**.

### BUG-004: Cost tracking неточный
**Описание:** Сначала используются **`usage.cost`** и разбор сырого JSON (см. **`docs/CURRENT_STATUS.md`**, раздел **`llm.py`**). Если провайдер не отдал **`usage.cost`** и нет **`x-openrouter-cost`**, остаётся грубая формула с hardcoded rates для gpt-4o-mini/gemini и generic rate ($0.1/$0.5 per 1M) для прочих моделей — возможна заметная ошибка относительно фактического счёта OpenRouter.
**Где:** `app/services/llm.py` → `generate_text()`
**Воспроизведение:** Запустить генерацию на GPT-5 → `total_cost` покажет в 10-50x меньше реальной стоимости если header не пришёл
**Ожидаемое поведение:** Использовать актуальные rates из OpenRouter API (`/api/v1/models`) или хотя бы расширить mapping
**Приоритет:** P2

### BUG-005: Settings API требует ручной рестарт
**Описание:** `PUT /api/settings/` пишет напрямую в .env файл через `dotenv.set_key()`, но Python-процесс уже загрузил конфигурацию через Pydantic Settings при старте. Новые значения не применяются до рестарта контейнеров.
**Где:** `app/api/settings_api.py` → `update_settings()`
**Воспроизведение:** Изменить OPENROUTER_API_KEY через UI → старый ключ продолжит использоваться
**Ожидаемое поведение:** Либо hot-reload конфигурации, либо явное предупреждение в UI с кнопкой рестарта
**Приоритет:** P2 (в UI уже есть warning, но нет кнопки рестарта)

### ~~BUG-006: Streamlit auto-rerun при processing создаёт нагрузку~~ ✅ ИСПРАВЛЕНО
**Описание:** Устранено в v2.0 (замена Streamlit на React SPA с TanStack Query).

### ~~BUG-007: Нет PUT endpoint для articles~~ ✅ ИСПРАВЛЕНО
**Описание:** Раньше не было HTTP-метода для правки статьи после генерации; ссылка «Export Word» с **`?format=docx`** на **`GET /articles/.../download`** не отдавала DOCX (игнорировался query).
**Исправление (апрель 2026):** **`PATCH /api/articles/{id}`** в **`app/api/articles.py`** — тело **`html_content`** (и опционально **`title`**, **`description`**); **`word_count`** пересчитывается через **`count_content_words`**; **`full_page_html`** сбрасывается при правке HTML. В **`GET /api/articles/{id}`** возвращается **`full_page_html`**. В React: **`ArticleDetailPage`** — вкладка **html**: один **Monaco** (read-only / edit) + Save, **Export DOCX** через **`?format=docx`** (см. **`docs/CURRENT_STATUS.md`**, DOCX и **«Monaco для HTML»**).
**Примечание:** автоматический re-injection в шаблон сайта после ручного редактирования не выполняется — превью использует **`full_page_html` || `html_content`**; после PATCH превью идёт из обновлённого **`html_content`**.

### ~~BUG-008: json_parser не обрабатывает все edge cases~~ ✅ ИСПРАВЛЕНО
**Описание (исторически):** В универсальном парсере был захардкожен поиск вложенного dict по ключам **`ai_structure_analysis`**, что мешало предсказуемости для других агентов; для **`meta_generation`** title/description терялись при обёртках и частично невалидном JSON.

**Исправление (апрель 2026, 11.04):** **`clean_and_parse_json(text, unwrap_keys=None)`** — размотка по **`unwrap_keys`** только там, где передано (вызов из **`phase_ai_structure`**); устойчивый разбор через **`raw_decode`** / regex. Модуль **`app/services/meta_parser.py`**: **`extract_meta_from_parsed`**, **`meta_variant_list`** — единый разбор title/description/H1 и списков вариантов (**`results`** / **`variants`**, без учёта регистра ключей и полей). Сборка статьи в **`pipeline.py`** через **`extract_meta_from_parsed`**, при наличии строки **`GeneratedArticle`** — её обновление; **`docx_builder._get_all_meta_from_task`** использует те же функции. Debug-логи сырого ответа, ключей **`meta_data`**, извлечённых полей. См. **`docs/CURRENT_STATUS.md`**, **11 апреля 2026**.

---

## 🟢 Мелкие (косметические / low impact)

### ~~BUG-020: Внешний импорт приватного `_auto_approve_images` из step-модуля~~ ✅ ИСПРАВЛЕНО (task50)
**Описание:** `app/services/pipeline/runner.py` импортирует helper `_auto_approve_images` из `app/services/pipeline/steps/image_gen_step.py`. По смыслу это часть pause/auto-mode orchestration в runner, а подчёркивание в имени указывает на модуль-приватность.
**Исправление:** helper перенесён в `app/services/pipeline/runner.py`; внешний импорт приватной функции из `steps/image_gen_step.py` удалён (commit `c11e092`).

### ~~BUG-017: Force Fail / Complete не работали для задач в статусе `stale`~~ ✅ ИСПРАВЛЕНО
**Описание:** **`POST /api/tasks/{id}/force-status`** принимал только **`processing`** → UI не мог принудительно завершить зависшую задачу после перевода в **`stale`**.
**Исправление (апрель 2026, 8.04):** разрешены статусы **`processing`** и **`stale`**; иначе **400**. **Дополнение (13.04.2026):** для паузы **SERP URL review** в **`force-status`** также разрешён **`paused`** (текст **400**: **`Only 'processing', 'stale', or 'paused' tasks can be forced`**). См. **`docs/CURRENT_STATUS.md`**, **8** и **13 апреля 2026**.

### BUG-012: Локальная сборка фронтенда падает на старом Node.js
**Описание:** `npm run build` запускает `tsc && vite build`. TypeScript 5 и Vite требуют **Node.js 18+**. На Node 12 (и частично 14) падает парсер (`Unexpected token ?` в `_tsc.js`), сборка невозможна.
**Где:** локальное окружение разработчика (не production Docker, если образ на node:20).
**Ожидаемое поведение:** Использовать `nvm`, `fnm` или Docker-образ фронтенда с актуальной LTS Node.
**Приоритет:** P4 (документация: `docs/TECH_STACK.md`)

### ~~BUG-009: Duplicate key в tasks list response~~ ✅ ИСПРАВЛЕНО
**Описание:** В старом `get_tasks()` поле **`page_type`** дублировалось в dict ответа элемента списка.
**Исправление (апрель 2026):** ответ списка заменён на **`{ "items": [...], "total": N }`**; в каждом элементе **`page_type`** один раз.

### BUG-010: User-Agent при скрапинге не ротируется
**Описание:** `scraper.py` использует один статичный User-Agent (`Chrome/91.0.4472.124`). Версия Chrome устаревшая (2021), что может триггерить bot-detection у некоторых сайтов.
**Где:** `app/services/scraper.py` → `scrape_urls()`, headers dict
**Ожидаемое поведение:** Пул из 5-10 актуальных User-Agent с рандомным выбором
**Приоритет:** P3

### ~~BUG-011: Frontend template upload field name mismatch~~ ✅ ИСПРАВЛЕНО
**Описание:** Устранено в v2.0 (замена Streamlit на React SPA с корректной типизацией).

### ~~BUG-013: Prompts Save визуально откатывал изменения и сбрасывал выбор агента~~ ✅ ИСПРАВЛЕНО
**Описание:** После сохранения промпта UI терял синхрон с сервером / выбором агента из-за версионирования через **`POST /`** и инвалидации кэша.
**Исправление (апрель 2026, доработка 3.04.2026 + task21):** основное сохранение — **`PUT /api/prompts/{id}`** (`updateInPlace`) с полями **`_*_enabled`**; в **`onSuccess`** — **`setQueryData`**, **`setEditState`**, **`setParamsEnabled`**, инвалидация **`['prompts']`**. Гидратация: `useEffect` с **`[derivedActiveId, fullPrompt?.id]`** и **`syncedPromptIdRef`** — однократная подстановка данных для каждого **`fullPrompt.id`**, без антипаттерна «флаг внутри колбэка **`setEditState`**» (см. **`docs/CURRENT_STATUS.md`**, раздел **«Model Settings: флаги *_enabled»**). Исторически: фиксы к **`POST`** и переключению `activePromptId` — см. архивные коммиты.

### ~~BUG-016: При выборе модели в Model Settings пропадали параметры и Save~~ ✅ ИСПРАВЛЕНО
**Описание:** После выбора модели в dropdown оставались только заголовок **Model Settings** и поле **Search models...**; остальные контролы визуально исчезали.
**Причина:** комбинация **`overflow-x-auto`** на строке панели (обрезка по оси Y для потомков) и **`position: absolute`** у выпадающего списка внутри того же контейнера; также риск сброса состояния при зависимости **`useEffect` от `fullPrompt`** (новая ссылка при каждом refetch).
**Исправление (3.04.2026):** список моделей — **`createPortal` в `document.body`** + **`position: fixed`** и обновление координат на scroll/resize; клик «вне» учитывает портал; зависимости гидратации — **`fullPrompt?.id`**; **`setEditState`**: при отсутствии `prev` возвращать **`prev`**, не **`null`**. См. **`docs/CURRENT_STATUS.md`**, **3 апреля 2026**.

### ~~BUG-014: Удаление сайта не проверяло задачи и проекты~~ ✅ ИСПРАВЛЕНО
**Описание:** `DELETE /api/sites/{id}` удаляло сайт и шаблоны без проверки ссылок из `tasks` (`target_site_id`) и `site_projects` (`site_id`).
**Исправление:** В `app/api/sites.py` перед удалением считаются зависимости; при `task_count > 0` или `project_count > 0` — **HTTP 409** с пояснением. В `SitesPage.tsx` в `onError` мутации удаления в toast выводится `response.data.detail` (строка или массив).

### ~~BUG-015: Белый экран после «Start Project» (422 + React #31)~~ ✅ ИСПРАВЛЕНО
**Описание:** (1) Форма **New Project** отправляла **`site_id`**, бэкенд ожидает **`target_site`** → **422 Unprocessable Entity**. (2) Глобальный Axios interceptor передавал в **`toast.error`** значение **`response.data.detail`** как есть; при ошибке валидации FastAPI это **массив объектов** — **react-hot-toast** пытался отрендерить его как React child → **React error #31**, белый экран без Error Boundary. (3) В **`GET /api/projects`** не было поля **`progress`**, таблица на списке проектов опиралась на него.
**Исправление:** Маппинг **`target_site`** в **`ProjectsPage.tsx`**; тип **`SiteProjectCreatePayload`** и **`projectsApi.create`** с **`skipErrorToast`**; **`formatApiErrorDetail`** в **`frontend/src/lib/apiErrorMessage.ts`** + использование в **`client.ts`** interceptor; **`onError`** мутации создаёт строку для toast; **`progress`** в **`get_projects`** (`app/api/projects.py`); **`RouteErrorBoundary`** вокруг **`Routes`** в **`App.tsx`**. Подробности: **`docs/CURRENT_STATUS.md`**, раздел **30 марта 2026 — Projects…**.