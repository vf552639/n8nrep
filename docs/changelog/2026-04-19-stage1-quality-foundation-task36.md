# 19 апреля 2026 — Этап 1: фундамент качества (task36)

**Дата:** 2026-04-19
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** снижение регрессий за счёт единого места для Pydantic-схем, задела под интеграционные тесты на Postgres, структурированных логов и переименования JSONB-логов выполнения.

**Инструментарий:** **`pyproject.toml`** (ruff, pytest, mypy на **`app/services/llm.py`**, **`json_parser.py`**, **`meta_parser.py`**), **`requirements-dev.txt`** (pytest, httpx, factory-boy, ruff, pre-commit, structlog и др.), **`.pre-commit-config.yaml`**.

**Схемы API:** **`app/schemas/`** — **`task`**, **`project`**, **`site`**, **`author`**, **`article`**, **`template`**, **`legal_page`**, **`blueprint`**, **`prompt`**, **`settings`**, **`serp_config`**, плюс контракты JSONB: **`step_result`**, **`log_event`**, **`jsonb_adapter`**, **`project_keywords`**. Роутеры **`app/api/*.py`** импортируют модели отсюда; **DoD task36 §1.2:** в каталоге **`app/api/`** нет подклассов **`BaseModel`** (в т. ч. **`app/api/tasks.py`** — только **`from app.schemas.task import ...`**, см. **«22 апреля 2026 — Этап 1: доводка»**).

**БД — `log_events`:** миграция **`t7u8v9w0x1yb`** (revises **`s6t7u8v9w0xe`**): **`tasks.log_events`**, **`site_projects.log_events`**; перенос из **`logs`** с усечением до **500** элементов; ORM **`app/models/task.py`**, **`app/models/project.py`**; запись в **`app/services/pipeline.py`** (**`add_log`**, лимит **500**), **`app/api/tasks.py`**, **`app/api/projects.py`**, **`app/workers/tasks.py`** (**`_append_project_log`**). Ответ **`GET /api/tasks/{id}`** отдаёт **`log_events`**.

**Structlog:** **`app/logging_config.py`** — связка structlog ↔ stdlib **`logging`**, отдельный классический **`FileHandler`** на **`logs/app.log`** (страница **Logs** в UI по-прежнему читает текстовый файл); консоль — JSON при **`LOG_JSON=true`**.

**Тесты и CI:** **`tests/conftest.py`** — при **`TEST_DATABASE_URL`** накатывается **`alembic upgrade head`**, фикстура **`db_session`** с откатом транзакции; **`pytest -m "not integration"`** в **`.github/workflows/ci.yml`** (Postgres/Redis сервисы, переменные **`SUPABASE_*`**, **`OPENROUTER_API_KEY`**, **`API_KEY=""`**). Интеграционные тесты: **`pytest -m integration`** при поднятом **`db-test`** или своей БД.

**Ограничения текущей итерации:** полный **`ruff check app/`** по старому коду не вычищен; в CI **`ruff`** ограничен **`app/schemas/`**, **`app/logging_config.py`**, **`app/workers/celery_app.py`**. Целевое покрытие **`app/api/`** из task36 — в работе (частично: smoke **GET**, см. **«22 апреля 2026 — Этап 1: доводка»**).

---
