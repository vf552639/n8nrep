# Апрель 2026 — task53 E: страницы проекта, БД-таймаут и диагностика ошибок

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст (план `task53.md`, раздел E):** длинные проекты падали на странице с обрезанным сообщением в логе проекта (**`[:200]`** от **`str(exception)`**); гипотеза — глобальный **`statement_timeout=60000`** мс на соединении SQLAlchemy обрывал тяжёлые коммиты с разросшимся JSONB **`step_results`**; любая ошибка пайплайна трактовалась как «skip page» и продвижение **`current_page_index`**, что для инфраструктурных сбоев БД нежелательно.

**`app/database.py`**
- В **`connect_args["options"]`** для движка: **`-c statement_timeout=600000`** (10 минут), чтобы worker-пайплайн реже получал **`canceling statement due to statement timeout`** на крупных **`UPDATE tasks`**.

**`app/workers/tasks.py` — `process_project_page`**
- **`OperationalError`**, **`DBAPIError`** вокруг **`run_pipeline`**: **`db.rollback()`**, повторная загрузка **`SiteProject`** / **`Task`**; задача страницы — **`pending`** (та же строка **`Task`** для повторного запуска), проект — **`pending`**; в **`project.log_events`** — краткое сообщение + хвост traceback (до 4000 символов во второй записи); **`advance_project.apply_async(args=[project_id, False], countdown=60)`** и **`return`** (без немедленного **`advance_project.delay`** в конце функции).
- Прочие исключения пайплайна: в **`project_task.error_log`** сохраняется **traceback** (хвост до 8000 символов), не только текст исключения.
- Сообщение **«Page … FAILED»** в лог проекта: **первая строка** из **`error_log`** (до 500 символов) + **`task_id=`** для открытия задачи в UI.

**Связь с остальным планом task53:** пункты **A–D** (таймауты LLM, fallback-модели, Executor step-timeout, **`celery_task_id`** + revoke) уже закрыты коммитом **`d78c5b8`** (**task52**); ротация **`log_events`** на уровне задачи (**E.3**, last 500) уже в **`app/schemas/jsonb_adapter.py`** / **`persistence.add_log`**.

---
