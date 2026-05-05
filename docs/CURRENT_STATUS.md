# ТЕКУЩИЙ СТАТУС ПРОЕКТА

**Дата последнего обновления:** май 2026 — длинный changelog вынесен в **`docs/changelog/`** ([индекс](changelog/README.md)). Ниже сохранены те же заголовки **`### …`** (якоря для ссылок из других документов): последние записи — полным текстом, остальные — краткий тизер и ссылка на файл.

---

### Май 2026 — task59 (UI): стабильность `Cluster Keywords` в черновиках проектов (`task59.md`)

**Контекст:** в `CreateProjectModal` кластеризация могла пропадать после открытия сохранённого черновика и неочевидно отрабатывать на длинных списках ключей (~90).

**Сделано**
- `ProjectsPage` (`CreateProjectModal`): удалён destructive `useEffect`, который очищал `clusterResult` после программного `setFormData(...)` при загрузке draft.
- Очистка `clusterResult` перенесена в user-driven `onChange` у `Blueprint` и `Additional Keywords` (functional updates `setFormData(prev => ...)` + `setClusterResult(null)`).
- `keyword_clusterer.py`: `max_tokens` увеличен с `4000` до `8000` для более длинных списков ключей.
- `keyword_clusterer.py`: добавлен `logger.info` с метриками `total_keywords`, `total_assigned`, `unassigned`, `response_length`, `model` для диагностики.
- UI: при успешной кластеризации с `total_assigned=0` добавлен явный `toast.error` (в дополнение к amber-баннеру), чтобы пользователь видел проблему сразу.

**Ожидаемый эффект:** кластер из `project_keywords.clustered` сохраняется при повторном открытии черновика; при длинных списках ключей результат чаще возвращается, а при пустом распределении пользователь получает явный сигнал и подсказку.

---

### Май 2026 — task58: per-page competitor URLs + `search_engine='off'` (`task58.md`)

**Контекст:** project-wide `competitor_urls` не покрывал кейс с разными конкурентами для разных страниц кластера. Дополнительно требовался явный режим отключения DataForSEO/SERP при запуске проекта.

**Сделано**
- Backend: `_validate_serp_config` принимает `search_engine='off'`.
- `SerpStep`: читаются per-page URL из `project_keywords.clustered[page_slug].competitor_urls`, fallback на `project.competitor_urls`.
- При `engine='off'` `fetch_serp_data()` не вызывается; `serp_data` формируется из пользовательских URL (`source='user_only'`) с warning-логом при пустом списке.
- При обычных engine сохранён fetch+merge; при наличии per-page URL они имеют приоритет над project-wide.
- UI `ProjectsPage`: добавлена опция `Off (skip DataForSEO)` в advanced SERP settings.
- UI `ProjectsPage`: под каждой карточкой `Keyword Distribution Preview` добавлен textarea `Competitor URLs` с сохранением в `project_keywords.clustered[slug].competitor_urls` и восстановлением в режиме `edit-draft`.
- Типы frontend (`api/projects.ts`, `types/project.ts`) расширены для `search_engine='off'` и `competitor_urls?: string[]` в clustered-элементе.
- Добавлены тесты: `tests/api/test_projects_serp_engine_off.py`, `tests/services/test_serp_step_per_page_urls.py`.

**Полный текст:** [changelog/2026-05-task58-per-page-competitor-urls-off-engine.md](changelog/2026-05-task58-per-page-competitor-urls-off-engine.md).

---

### Май 2026 — task55: Blueprints/Legal visibility + editable clustering preview (`task55.md`)

**Контекст:** в `Create Project` legal-блок зависел от фактических `page_type` в `blueprint_pages`, но в UI Blueprints не было явного индикатора «как сохранено в БД». Плюс результат `Cluster Keywords` был read-only: нельзя удалить шумные ключи и переназначить ключ между страницами.

**Сделано**
- `BlueprintsPage` (таблица Pages): в колонке Type добавлен label + monospace badge с **raw `page_type`** из записи.
- `CreateBlueprintModal` / `AddBlueprintPageModal` / `EditBlueprintPageModal` / delete page: в `onError` используется `formatApiErrorDetail(...)`, чтобы показывать backend detail (а не только generic toast).
- `ProjectsPage` (`Keyword Distribution Preview`): внедрён локальный `KeywordChip` с двумя действиями:
  - hover `×` — удалить keyword из текущего cluster preview;
  - click — меню переноса keyword в любую страницу или в `Unassigned`.
- Добавлены pure-хелперы `removeKeyword(...)` и `moveKeyword(...)` с пересчётом `total_assigned`; перемещение в текущую секцию отключено (no-op).
- Добавлена заметка в UI: правки применяются только к текущему cluster result; re-cluster берёт исходный список из textarea.

**Полный текст:** [changelog/2026-05-task55-blueprints-clustering-ux.md](changelog/2026-05-task55-blueprints-clustering-ux.md).

---

### Май 2026 — task53: черновики проектов (модалка Add Project, `task53.md`)

**Контекст:** в попапе «New Project» нужно сохранять неполную форму и возвращаться к ней позже; минимальное требование к черновику — только имя проекта.

**Сделано**
- Статус **`draft`** у **`site_projects`**; миграция **`z2a3b4c5d6e7`**: nullable **`blueprint_id`**, **`site_id`**, **`seed_keyword`**, **`country`**, **`language`**; колонка **`target_site`** (до запуска — UUID выбранного сайта из селекта или пусто для markup-only).
- API: **`POST /projects/draft`**, **`PATCH /projects/{id}`** (только **`status == draft`**), **`POST /projects/{id}/launch`** (та же валидация и очередь Celery, что у **`POST /projects`**, с **`_ensure_worker_available()`** до смены статуса с черновика; duplicate-check не учитывает **`draft`** и не конфликтует с текущей строкой при launch).
- **`POST /projects`** и **clone**: в duplicate-фильтре статусы **`failed`** и **`draft`**; clone источника без **`site_id`** требует **`target_site`** в теле.
- **Фронт:** **`ProjectsPage`** / **`CreateProjectModal`** — **Save Draft**, **Launch Project**, фильтр и бейдж **Draft**, клик по строке черновика открывает редактирование; **`projectsApi`**, типы **`Project`**.
- **`ProjectDetailPage`:** прямой заход по URL на черновик → редирект на список проектов.

**Полный текст:** [changelog/2026-05-task53-project-drafts-modal.md](changelog/2026-05-task53-project-drafts-modal.md).

---

### Май 2026 — task51: снижение egress Supabase (`task51.md`)

**Контекст:** повторяющиеся полные выборки таблицы **`authors`** (все Text-поля на каждом монтировании страниц и при **`refetch`**) и второй **`SELECT`** автора в одном прогоне пайплайна (**`setup_template_vars`** + **`_apply_author_footer`**) раздували исходящий трафик к managed Postgres (Supabase).

**Сделано**
- **`GET /api/authors/`**: параметры **`limit`** (1–500, по умолчанию 100), **`offset`**, **`full`** (по умолчанию выключен). В лёгком режиме из БД читаются только **`id`, author, country, country_full, language, year`**; тяжёлые Text-колонки — при **`full=1`**; **`usage_count`** считается только для авторов на текущей «странице» выборки; ответ списка кэшируется in-process **60 с**, сброс при создании/обновлении/удалении автора (**`app/api/authors.py`**).
- **Фронт:** **`authorsLightListQueryOptions`** / **`authorsFullListQueryOptions`** в **`frontend/src/api/authors.ts`** (**`staleTime` 5 мин**, ключи **`["authors","light"]`** и **`["authors","full"]`**); лёгкий список для селектов (**ProjectsPage**, **ProjectDetailPage** clone, **SitesPage**, **TasksPage**); полный список на **AuthorsPage** (**`full=true`**).
- **Пайплайн:** при создании **`PipelineContext`** один раз загружается **`ctx.author`**; **`template_vars.setup_template_vars`** и **`assembly._apply_author_footer`** используют его вместо повторных **`query(Author)`** (**`app/services/pipeline/context.py`**, **`template_vars.py`**, **`assembly.py`**).
- **Тесты:** расширен **`tests/api/test_authors_api.py`** (лёгкий ответ без **`bio`**, полный с **`bio`**, параметры **`limit`/`offset`**).

---

### Май 2026 — Blueprint: per-page `hide_author_geo` (футер автора, `task50.md`, commit `f4ff8d8`)

**Сделано**
- `blueprint_pages`: добавлен булев флаг `hide_author_geo` (default `false`) + миграция `y1z2a3b4c5d6`.
- `app/services/template_engine.py`: `render_author_footer(author, hide_geo=False)` — при `hide_geo=True` не рендерит «Страна», «Код страны», «Город».
- `app/services/pipeline/assembly.py`: флаг читается из `ctx.blueprint_page.hide_author_geo` и пробрасывается в рендер футера; fallback при отсутствии `blueprint_page` — `hide_geo=False`.
- `app/api/blueprints.py` и схемы/типы: поле добавлено в create/update/read для страниц blueprint.
- UI `BlueprintsPage`: чекбокс «Скрыть страну/город автора в футере» в Add/Edit модалках страницы blueprint.

**Ожидаемый эффект:** для мультиязычных slot-страниц можно сохранить стиль автора, но убрать визуально конфликтующие GEO-поля автора в HTML-футере на уровне конкретной страницы blueprint.

---

### Апрель 2026 — task60: security hardening API/infra

**Сделано**
- **Auth/CORS:** `app/config.py` — `AUTH_DISABLED` + валидация `API_KEY`; `app/api/deps.py` — auth bypass только при `AUTH_DISABLED=true`; `app/main.py` — при wildcard CORS отключаются credentials.
- **SSRF:** новый `app/utils/url_safety.py` (`raise_if_url_unsafe_for_ssrf`, `safe_requests_get_bytes`); проверки в `POST /api/tasks/fetch-url-meta`, `app/services/scraper.fetch_url_meta`, `app/services/image_hosting.ImgBBUploader.upload_from_url`.
- **Bulk CSV:** `app/api/tasks.py` — лимит размера (1 MiB), лимит строк (500), обязательные колонки, UTF-8 и content-type валидация, понятные 4xx-ответы.
- **Infra:** `Dockerfile` и `frontend/Dockerfile` переведены на non-root пользователя; `app/database.py` `pool_timeout` уменьшен до 10 с.
- **Observability/security headers:** `app/services/llm.py` — `print` заменён на logger, `OPENROUTER_HTTP_REFERER` вынесен в config; `app/main.py` — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.
- **CI/tests/docs:** workflow дополнен `npm run lint`, `npm run typecheck`, `pip-audit`/`npm audit` (soft-fail); добавлен `tests/unit/test_url_safety.py`; обновлены `.env.example`, `README.md`, тестовые фикстуры auth.

---

### Апрель 2026 — task59: `PendingRollbackError` после обрыва соединения к БД во время LLM

**Контекст:** на длинных вызовах OpenRouter (`reader_opinion` и др.) прогресс-колбэки пишут логи через **`add_log`** → **`commit()`**. После commit ORM-атрибуты **`task`** по умолчанию истекают; следующий доступ к **`task.log_events`** делает lazy **`SELECT`**. Если за время простоя Supavisor/NAT оборвал TCP, **`OperationalError`** оставлял сессию в состоянии pending rollback; общий **`except`** в **`generate_text`** / отсутствие **`rollback`** в **`call_agent`** и **`runner`** приводило к **`PendingRollbackError: Can't reconnect until invalid transaction is rolled back`** в логе пайплайна.

**Сделано**
- **`app/database.py`**: **`SessionLocal(..., expire_on_commit=False)`** — после commit не триггерить лишние lazy-load по мёртвому соединению; **`pool_recycle=settings.DB_POOL_RECYCLE_SECONDS`** (по умолчанию **60**); в **`connect_args`** — **`keepalives`**, **`keepalives_idle`**, **`keepalives_interval`**, **`keepalives_count`** наряду с **`statement_timeout=600000`**.
- **`app/config.py`**: **`DB_POOL_RECYCLE_SECONDS: int = 60`** (переопределение через env).
- **`app/services/pipeline/llm_client.py`**: **`_safe_db`** — любая ошибка в колбэках прогресса / heartbeat → **`rollback()`** + structlog **`call_agent_suppressed_callback_db_error`** (не пробрасывает ошибку в **`generate_text`**); **`rollback`** перед **`raise`** из **`InsufficientCreditsError`** и перед обёрткой в **`LLMError`**.
- **`app/services/pipeline/runner.py`**: в ветке retry по **`step.policy.retryable_errors`** — **`rollback()`** до **`add_log`** с текстом «↩️ retry».
- **`app/workers/tasks.py`**: **`rollback()`** в общем **`except`** после **`run_pipeline`** в **`process_project_page`** и в **`process_generation_task`** перед повторными запросами к БД.
- **`tests/services/test_llm_client_callback_db.py`**: регрессия — **`OperationalError`** при первом **`add_log`** на **`response_received`**, затем успешное завершение **`generate_text`**.

**Ожидаемый эффект:** страницы проекта и одиночные задачи не падают цепочкой с **`PendingRollbackError`** после сетевого обрыва во время LLM; в логах воркера при реальных обрывах возможны предупреждения **`call_agent_suppressed_callback_db_error`**.

---

### Апрель 2026 — task58: нормализация `authors.country` в форме Authors

**Контекст:** в `AuthorsPage` поле страны было свободным текстом; в БД появились записи вида `CANADA`, тогда как Projects-фильтрация ожидает ISO-коды (`CA`, `PL`, `FR`) и сравнивает строки строго. Это ломало подбор авторов по Country/Language в форме проектов.

**Сделано**
- `frontend/src/pages/AuthorsPage.tsx`: добавлен импорт `COUNTRIES`, `COUNTRY_CODES`, `countryLabel`.
- В `AuthorFormFields` поле **«Страна»** заменено на `<select required>` по каноническому списку стран (`COUNTRIES`) с отображением `Label (CODE)`.
- Добавлен helper `canonicalCountryCode(raw)` для нормализации и валидации выбранного кода.
- При выборе страны форма синхронно обновляет `country` (ISO-код) и `country_full` (человеко-читаемое название через `countryLabel`).
- Поле `country_full` переведено в `readOnly/disabled`, чтобы не создавать новый рассинхрон.
- В create/edit submit добавлена проверка валидного ISO-кода; в API отправляется канонический payload (`country=CODE`, `country_full=countryLabel(CODE)`).
- Для существующих неканонических значений (`Canada`/`CANADA`) добавлена подсказка в форме о необходимости выбрать страну из списка и пересохранить автора.

**Ожидаемый эффект:** новые и отредактированные авторы сохраняются только с ISO-кодом, а фильтры и автоподбор автора в Projects снова работают предсказуемо для `CA`.

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

**Контекст:** на проектных страницах наблюдались (1) падения commit с `ValueError: ... NUL (0x00)` при записи scraped/serp данных в Postgres и (2) неэффективные повторы LLM-вызовов при OpenRouter `402…

**Полный текст:** [changelog/2026-04-task54-nul-sanitize-openrouter-402.md](changelog/2026-04-task54-nul-sanitize-openrouter-402.md).

---

### Апрель 2026 — task53 E: страницы проекта, БД-таймаут и диагностика ошибок

**Контекст (план `task53.md`, раздел E):** длинные проекты падали на странице с обрезанным сообщением в логе проекта (**`[:200]`** от **`str(exception)`**); гипотеза — глобальный **`statement_timeout=…

**Полный текст:** [changelog/2026-04-task53e-project-page-db-resilience.md](changelog/2026-04-task53e-project-page-db-resilience.md).

---

### Апрель 2026 — task52: зависания LLM-шагов, таймауты и revoke Celery

**Контекст:** длинные вызовы (напр. `gpt-5-mini` с reasoning и большим контекстом) + ретраи `generate_text` и exclude-words выходили за **`STEP_TIMEOUT_MINUTES`** / stale в Beat; **`SIGALRM`** в worke…

**Полный текст:** [changelog/2026-04-task52-llm-step-timeouts-revoke.md](changelog/2026-04-task52-llm-step-timeouts-revoke.md).

---

### Апрель 2026 — task50: сверка плана после удаления legacy

Контекст: после пуша финальных изменений по декомпозиции pipeline требовалась проверка `plan1.md` относительно фактического состояния `origin/main`.

**Полный текст:** [changelog/2026-04-task50-pipeline-followup.md](changelog/2026-04-task50-pipeline-followup.md).

---

### Апрель 2026 — task48: стабилизация pipeline runner + e2e smoke

Контекст: после task47 оставались риски в policy/error-path и два «живых» дефекта в `tests/services/test_pipeline_e2e_smoke.py` (патч не в те bindings шагов и запуск без `auto_mode=True`, что приводило к `paused` на `ser…

**Полный текст:** [changelog/2026-04-task48-pipeline-runner-stabilization.md](changelog/2026-04-task48-pipeline-runner-stabilization.md).

---

### Апрель 2026 — task45 (Шаг 4): Context + Assembly, статус

Сделано

**Полный текст:** [changelog/2026-04-task45-context-assembly.md](changelog/2026-04-task45-context-assembly.md).

---

### Апрель 2026 — task46: контракт `finalize_article` + unit-тесты

Сделано

**Полный текст:** [changelog/2026-04-task46-finalize-article-contract.md](changelog/2026-04-task46-finalize-article-contract.md).

---

### Апрель 2026 — task47: аудит step-классов (без правок кода)

Артефакт

**Полный текст:** [changelog/2026-04-task47-step-classes-audit.md](changelog/2026-04-task47-step-classes-audit.md).

---

### Апрель 2026 — task43: декомпозиция pipeline (A–E, F1–F10)

Контекст: после выделения каркаса `app/services/pipeline/` и плана task42 выполнен основной перенос логики из `app/services/_pipeline_legacy.py` в пакет с шагами.

**Полный текст:** [changelog/2026-04-task43-pipeline-decomposition.md](changelog/2026-04-task43-pipeline-decomposition.md).

---

### 22 апреля 2026 — taskco: wire-up и quality gates

Контекст: закрытие оставшихся пробелов по task36: использование JSONB-адаптеров в рантайме, более реалистичные интеграционные тесты Celery/pipeline, и включение жёстких CI-гейтов по coverage.

**Полный текст:** [changelog/2026-04-22-taskco-wireup-quality-gates.md](changelog/2026-04-22-taskco-wireup-quality-gates.md).

---

### 22 апреля 2026 — task42: план декомпозиции pipeline.py

**Контекст:** `app/services/pipeline.py` разросся до **2579 строк** и совмещает пять несвязанных обязанностей: оркестрация, 21 phase-функция, построение `PipelineContext`, подготовку переменных, сборк…

**Полный текст:** [changelog/2026-04-22-task42-pipeline-decomposition-plan.md](changelog/2026-04-22-task42-pipeline-decomposition-plan.md).

---

### 23 апреля 2026 — Этап 1: task37 (API happy-path тесты)

Контекст: вместо одного параметризованного smoke-теста по GET роутерам добавлен набор по-роутерных happy-path тестов для API с CRUD-сценариями и базовыми регрессиями по `tasks/projects`.

**Полный текст:** [changelog/2026-04-23-task37-api-happy-path-tests.md](changelog/2026-04-23-task37-api-happy-path-tests.md).

---

### 19 апреля 2026 — Этап 1: фундамент качества (task36)

Контекст: снижение регрессий за счёт единого места для Pydantic-схем, задела под интеграционные тесты на Postgres, структурированных логов и переименования JSONB-логов выполнения.

**Полный текст:** [changelog/2026-04-19-stage1-quality-foundation-task36.md](changelog/2026-04-19-stage1-quality-foundation-task36.md).

---

### 22 апреля 2026 — Этап 1: доводка (tasks API, smoke-тесты, DoD 1.2)

Контекст: закрытие регрессии после `logs` → `log_events`, устранение дублирования Pydantic-моделей в `app/api/tasks.py`, минимальные HTTP-smoke-тесты и явный прогон миграций в CI.

**Полный текст:** [changelog/2026-04-22-stage1-tasks-api-smoke-dod12.md](changelog/2026-04-22-stage1-tasks-api-smoke-dod12.md).

---

### 21 апреля 2026 — Legal: `primary_generation_legal`, inject, критичные переменные

**Контекст:** у **`LegalPageTemplate`** контент образца может быть **plain text** или **HTML** (**`content_format`**), есть **`notes`**. Промпт **`primary_generation_legal`** и подстановки в пайплайне…

**Полный текст:** [changelog/2026-04-21-legal-primary-generation-inject.md](changelog/2026-04-21-legal-primary-generation-inject.md).

---

### 21 апреля 2026 — task41: пользовательские URL конкурентов для проекта

**Контекст:** для страниц проекта конкуренты по умолчанию берутся только из SERP (DataForSEO / SerpAPI). Нужно вручную задать дополнительные URL на **`SiteProject`**, смержить их с органикой SERP, убр…

**Полный текст:** [changelog/2026-04-21-task41-project-competitor-urls.md](changelog/2026-04-21-task41-project-competitor-urls.md).

---

### 20 апреля 2026 — Markup only: создание проекта без Target Site

Контекст: нужна генерация «только разметка» (content-only) без привязки к реальному сайту и без HTML-обёртки (head / header / footer). Колонка `site_projects.site_id` остаётся NOT NULL — миграции БД не требуются.…

**Полный текст:** [changelog/2026-04-20-markup-only-projects.md](changelog/2026-04-20-markup-only-projects.md).

---

### 20 апреля 2026 — task40: гарантированные meta-теги и блок автора в финальном HTML

**Контекст:** для страниц проектов без активной обёртки сайта (или при шаблоне без плейсхолдеров `title/description`) часть non-main страниц уходила в экспорт без корректного `<head>` (`<title>`, `<me…

**Полный текст:** [changelog/2026-04-20-task40-meta-tags-author-footer.md](changelog/2026-04-20-task40-meta-tags-author-footer.md).

---

### 19 апреля 2026 — HTML-экспорт страниц (MODX / Source)

**Контекст:** экспорт в DOCX искажает разметку при переносе в MODX; контент-менеджерам нужен **чистый HTML** тела страницы (как в **`GeneratedArticle.html_content`**, без обёртки сайта), с сохранением…

**Полный текст:** [changelog/2026-04-19-html-export-modx.md](changelog/2026-04-19-html-export-modx.md).

---

### 19 апреля 2026 — Зависшие проекты: force-delete, массовое удаление, reset-status, каскад сайта

Контекст: если Celery падает без обработки, проект мог оставаться в `pending`/`generating` и не удалялся обычным `DELETE`. Нужны явные операции восстановления и каскадное удаление сайта с проектами.

**Полный текст:** [changelog/2026-04-19-stuck-projects-force-delete.md](changelog/2026-04-19-stuck-projects-force-delete.md).

---

### 18 апреля 2026 — Sites API и чекбокс Use site HTML template

**Цель:** UI **Create Generative Project** стабильно отражает наличие HTML-шаблона у сайта (**`sites.template_id`**), в т.ч. после частичного деплоя и при устаревшем кэше React Query; пользователь все…

**Полный текст:** [changelog/2026-04-18-sites-api-use-template-checkbox.md](changelog/2026-04-18-sites-api-use-template-checkbox.md).

---

### 18 апреля 2026 — Language: INITCAP и защита на фронте

Проблема (закрыта): в дропдаунах Language дублировались значения с разным регистром (`French` / `french`); при выборе нижнего регистра фильтр авторов по `===` не находил записей с `French`.

**Полный текст:** [changelog/2026-04-18-language-initcap-frontend.md](changelog/2026-04-18-language-initcap-frontend.md).

---

### 18 апреля 2026 — Legal templates: дефолт на Blueprint, override в Project, фолбек в pipeline

Цель: три уровня выбора reference-шаблона для legal-страниц: явный выбор в проекте → дефолт страницы блупринта → генерация без reference.

**Полный текст:** [changelog/2026-04-18-legal-templates-blueprint-default.md](changelog/2026-04-18-legal-templates-blueprint-default.md).

---

### 18 апреля 2026 — LegalPageTemplate: удаление поля `title`

Цель: единственный человекочитаемый идентификатор шаблона в списках и формах — `name` (плюс `page_type`); колонка `title` в БД и API убрана.

**Полный текст:** [changelog/2026-04-18-legal-page-template-drop-title.md](changelog/2026-04-18-legal-page-template-drop-title.md).

---

### 18 апреля 2026 — Проект: `use_site_template` (обёртка сайта опционально)

**Цель:** шаблон HTML остаётся привязанным к **`Site.template_id`**, но для конкретного **`SiteProject`** можно отключить использование обёртки: статьи — «сырой» HTML без head/CSS/header/footer; **`si…

**Полный текст:** [changelog/2026-04-18-project-use-site-template.md](changelog/2026-04-18-project-use-site-template.md).

---

### 16 апреля 2026 — Защитная инфраструктура: 500 как JSON, миграции, пул БД, Alembic DDL

Контекст: инцидент с неприменённой миграцией и `idle in transaction` на Supavisor — 500 отдавались как `text/plain`, фронт показывал «Network Error»; расхождение ревизии БД и кода не было видно при старте.

**Полный текст:** [changelog/2026-04-16-defensive-infra-500-json-alembic.md](changelog/2026-04-16-defensive-infra-500-json-alembic.md).

---

### 15 апреля 2026 — `phase_image_inject`: корректный инжект по `<!-- MEDIA: ... -->`

**Проблема (закрыта):** после `html_structure` в тексте уже нет маркеров `[MULTIMEDIA ...]` — они конвертируются в HTML-комментарии `<!-- MEDIA: ... -->`. Из-за этого `phase_image_inject` не находил м…

**Полный текст:** [changelog/2026-04-15-phase-image-inject-media-comments.md](changelog/2026-04-15-phase-image-inject-media-comments.md).

---

### 15 апреля 2026 — DOCX: тело статьи из шагов без «перехвата» `final_editing`

**Проблема (закрыта):** при пустом **`article.html_content`** (реран, сборка не записалась и т.п.) **`_get_content_from_task`** уходил во внутренний **`from_final()`** и брал **только** результат шага…

**Полный текст:** [changelog/2026-04-15-docx-body-without-final-editing.md](changelog/2026-04-15-docx-body-without-final-editing.md).

---

### 14 апреля 2026 — SERP URL review: автопарсинг title/description + fallback в pipeline

**Проблема (закрыта):** при ручном добавлении URL в SERP review (`approve-serp-urls`) новые `organic_results` создавались с пустыми `title/description`, из-за чего переменные промптов `{{competitor_ti…

**Полный текст:** [changelog/2026-04-14-serp-url-review-meta-autoparse.md](changelog/2026-04-14-serp-url-review-meta-autoparse.md).

---

### 13 апреля 2026 — Пауза после SERP: ревью и редактирование URL конкурентов

**Контекст:** между SERP и scraping пользователь должен иметь возможность убрать «мусорные» URL и добавить свои (например из Ahrefs). Аналогия с паузой **`image_review`**, но для одиночных (**не проек…

**Полный текст:** [changelog/2026-04-13-serp-url-review-pause.md](changelog/2026-04-13-serp-url-review-pause.md).

---

### 11 апреля 2026 — JSON-парсер, `meta_generation`, Top P в Model Settings (UI)

**Контекст:** доработки по task25 — корректное извлечение title/description из ответа **`meta_generation`**; универсальный парсер JSON без хардкода ключей **`ai_structure_analysis`**; визуальная согла…

**Полный текст:** [changelog/2026-04-11-json-parser-meta-generation-top-p.md](changelog/2026-04-11-json-parser-meta-generation-top-p.md).

---

### 8 апреля 2026 — LLM: не передавать `top_p` / penalties в API при `*_enabled = False`; Force Fail/Complete для `stale`

**Проблема (закрыта):** при выключенных тогглах в запрос всё равно уходили **`top_p=1.0`**, **`frequency_penalty=0`**, **`presence_penalty=0`** — часть моделей на OpenRouter ведёт себя иначе, чем при …

**Полный текст:** [changelog/2026-04-08-llm-no-top-p-penalties-when-disabled.md](changelog/2026-04-08-llm-no-top-p-penalties-when-disabled.md).

---

### 6 апреля 2026 — Pipeline Presets (набор шагов per страница блупринта)

Проблема (закрыта): один глобальный режим «SERP / не SERP» для всех страниц без SERP не подходил для About, Legal, Category vs полной статьи.

**Полный текст:** [changelog/2026-04-06-pipeline-presets-per-page.md](changelog/2026-04-06-pipeline-presets-per-page.md).

---

### Апрель 2026 — Monaco для HTML: Article Review, Article Detail; ручное сохранение `step_results`

Backend (`app/api/tasks.py`):

**Полный текст:** [changelog/2026-04-monaco-html-article-review.md](changelog/2026-04-monaco-html-article-review.md).

---

### Апрель 2026 — `llm.py`: стоимость и токены из сырого ответа OpenRouter; логи pipeline

`app/services/llm.py` (`generate_text`):

**Полный текст:** [changelog/2026-04-llm-cost-tokens-from-raw.md](changelog/2026-04-llm-cost-tokens-from-raw.md).

---

### Апрель 2026 — DOCX одиночной статьи/задачи: шапка H1 и строка Title в таблице

`app/services/docx_builder.py` (`build_single_article_docx`, `_add_simple_article_meta_table`):

**Полный текст:** [changelog/2026-04-docx-single-article-h1-header.md](changelog/2026-04-docx-single-article-h1-header.md).

---

### Апрель 2026 — Model Settings: флаги `*_enabled` (task21), pipeline и гидратация UI

Проблема (закрыта): тогглы Max tokens / Temperature / Freq. / Pres. / Top P «угадывались» по числовым значениям; `isDirty` и сохранение расходились с ожиданиями; при refetch React Query форма могла рассинхронизироваться.…

**Полный текст:** [changelog/2026-04-model-settings-enabled-flags.md](changelog/2026-04-model-settings-enabled-flags.md).

---

### 3 апреля 2026 — Prompts: сохранение in-place, Model Settings UI, фикс выбора модели

Backend (`app/api/prompts.py`)

**Полный текст:** [changelog/2026-04-03-prompts-save-in-place-model-settings.md](changelog/2026-04-03-prompts-save-in-place-model-settings.md).

---

### 2 апреля 2026 — Pipeline: контекст шага `final_editing`

`app/services/pipeline.py`, `phase_final_editing`:

**Полный текст:** [changelog/2026-04-02-pipeline-final-editing-context.md](changelog/2026-04-02-pipeline-final-editing-context.md).

---

### 2 апреля 2026 — DOCX: одиночная статья и одиночная задача

Backend (`app/services/docx_builder.py`)

**Полный текст:** [changelog/2026-04-02-docx-single-article-task.md](changelog/2026-04-02-docx-single-article-task.md).

---

### 2 апреля 2026 (вторая итерация) — Инфраструктура, API, React UI

Инфраструктура

**Полный текст:** [changelog/2026-04-02-infra-api-react-iteration2.md](changelog/2026-04-02-infra-api-react-iteration2.md).

---

### 2 апреля 2026 — Проекты: DOCX, additional keywords, формат meta_generation

**Проблема (исправлено):** ответ `meta_generation` в виде `{"results": [{Title, Description, H1, Trigger}, …]}` не содержит ключей `title`/`description` на верхнем уровне — в **`pipeline.py`** при сбо…

**Полный текст:** [changelog/2026-04-02-projects-docx-additional-keywords.md](changelog/2026-04-02-projects-docx-additional-keywords.md).

---

### 1 апреля 2026 — Templates, Legal Pages, связь Site → Template

Модели и БД

**Полный текст:** [changelog/2026-04-01-templates-legal-pages-site-link.md](changelog/2026-04-01-templates-legal-pages-site-link.md).

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

Backend (`app/workers/tasks.py`, `app/services/pipeline.py`, `app/services/llm.py`, `app/config.py`, `app/workers/celery_app.py`):

**Полный текст:** [changelog/2026-03-31-pipeline-observability-isolated-pages.md](changelog/2026-03-31-pipeline-observability-isolated-pages.md).

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

**Статус:** React SPA (v2.0) в продакшене. Текущий инженерный фокус Q2 2026 — **Quality Gate**, расширение **fallback** моделей и устойчивость long-running задач; сводный бэклог — [Roadmap.md](Roadmap.md#текущий-бэклог). Ниже — архивные заметки по эволюции Prompts / Projects / Tasks (март–апрель 2026) в формате тизер + полный текст в `changelog/`.

### Март 2026 — страница Prompts («SEO Workflow Optimizer») и API

Цель: единая рабочая область для редактирования промптов агентов пайплайна с тестом LLM, переменными и версиями.

**Полный текст:** [changelog/2026-03-prompts-page-seo-workflow-optimizer.md](changelog/2026-03-prompts-page-seo-workflow-optimizer.md).

---

### Март–апрель 2026 — обновления (стабильность `html_structure`, промпты, UI)

Шаг `html_structure` (снижение потери контента, `app/services/pipeline.py`):

**Полный текст:** [changelog/2026-03-04-html-structure-stability-prompts-ui.md](changelog/2026-03-04-html-structure-stability-prompts-ui.md).

---

### Март 2026 — Sites, Blueprints, Projects (формы и API)

Sites (`SitesPage.tsx`, `app/api/sites.py`):

**Полный текст:** [changelog/2026-03-sites-blueprints-projects-forms-api.md](changelog/2026-03-sites-blueprints-projects-forms-api.md).

---

### 30 марта 2026 — Projects: `POST` body, `GET` progress, Axios toast, Error Boundary

Backend (`app/api/projects.py`):

**Полный текст:** [changelog/2026-03-30-projects-post-body-axios-toast.md](changelog/2026-03-30-projects-post-body-axios-toast.md).

---

### 30 марта 2026 — Проекты: архивация, устойчивость к сбоям SERP, расширение API и UI

Модель и миграция

**Полный текст:** [changelog/2026-03-30-projects-archive-serp-resilience.md](changelog/2026-03-30-projects-archive-serp-resilience.md).

---

### Март 2026 — Проекты: preview (dry-run), SERP-конфиг, CSV, health-check SERP

Цель: планировать запуск без записи в БД, задавать SERP на уровне проекта, выгружать отчёты и видеть состояние SERP API до старта.

**Полный текст:** [changelog/2026-03-projects-preview-serp-config-csv.md](changelog/2026-03-projects-preview-serp-config-csv.md).

---

### Март 2026 — Задачи (Tasks), деталь задачи, шаги pipeline (StepCard)

Цель: выборочный запуск задач, человекочитаемые шаги SERP/Scraping, табы результата/промптов/переменных для LLM-шагов, рабочие execution logs, без дублирующих табов.

**Полный текст:** [changelog/2026-03-tasks-detail-step-card.md](changelog/2026-03-tasks-detail-step-card.md).

---

### Март 2026 — Image pipeline (актуализация)

- Для выполнения image-цепочки должны быть заданы: `IMAGE_GEN_ENABLED=true`, `GOAPI_API_KEY`, `IMGBB_API_KEY`.

**Полный текст:** [changelog/2026-03-image-pipeline-update.md](changelog/2026-03-image-pipeline-update.md).

---

### Март 2026 — SERP/Scraping cache (актуализация)

- `fetch_serp_data()` обёрнут в Redis-кэш финального результата (`_from_cache` пробрасывается в `step_results.serp_research.result`).

**Полный текст:** [changelog/2026-03-serp-scraping-cache-update.md](changelog/2026-03-serp-scraping-cache-update.md).

---

### 28 марта 2026 — статьи: `meta_data`, контроль слов по шагам

**Актуализация (2.04.2026):** если JSON от `meta_generation` имеет вид **`{"results": [...]}`**, поля **`title`/`description` статьи** заполняются из **первого варианта** (ключи `Title`/`Description` …

**Полный текст:** [changelog/2026-03-28-articles-meta-data-word-count.md](changelog/2026-03-28-articles-meta-data-word-count.md).

---

### 28 марта 2026 — парсер MULTIMEDIA для image pipeline (`image_utils.py`)

Проблема: outline на языке статьи даёт ключи вроде `МУЛЬТИМЕДИА`, `MULTIMÉDIA`, `medien` и т.д.; раньше искалось только английское `MULTIMEDIA`.

**Полный текст:** [changelog/2026-03-28-multimedia-parser-image-pipeline.md](changelog/2026-03-28-multimedia-parser-image-pipeline.md).

---

### 28 марта 2026 — `max_tokens` в LLM (OpenRouter)

Проблема: лимит вывода из поля `prompts.max_tokens` в БД не передавался в Chat Completions — провайдер использовал дефолт модели.

**Полный текст:** [changelog/2026-03-28-max-tokens-llm-openrouter.md](changelog/2026-03-28-max-tokens-llm-openrouter.md).

---

### v2.0: исторический спринт React и hotfixes (архив)

Сводка завершённого спринта миграции UI и списка hotfixes по Prompts/Tasks/Articles — перенесена в [changelog/2026-03-v2-legacy-sprint-and-hotfixes.md](changelog/2026-03-v2-legacy-sprint-and-hotfixes.md).

---

## 📋 Следующие задачи

См. [Roadmap.md](Roadmap.md#текущий-бэклог).

---

## 🐛 Известные проблемы

См. [Bugs.md](Bugs.md#известные-ограничения).

---

## 💡 Идеи для улучшения

См. [Roadmap.md](Roadmap.md#идеи).
