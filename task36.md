# План реализации: Этап 1 — Фундамент качества

## Контекст

Соло-разработчик, проект вышел из фазы фичеризации, 20 последних коммитов — фиксы. Чтобы новые фичи не плодили регрессии, нужно заложить **тестовую сетку, типизацию JSONB и структурированные логи**. Этот документ — пошаговый ТЗ по Этапу 1 на 2–3 недели.

**Что есть сейчас (факты из разведки):**
- Тесты: 8 файлов на `unittest.mock.MagicMock`, нет `conftest.py`, нет тестовой БД, нет `pytest-asyncio`/`httpx`, нет `factory_boy`
- API: 14 роутеров, `tasks.py` — 1168 строк, `projects.py` — 1214 строк, Pydantic-схемы живут **внутри роутеров**, папки `app/schemas/` **нет**
- Auth: `verify_api_key` через header `X-API-Key` (может быть пустым)
- Логирование: стандартный `logging`, `logger = logging.getLogger(__name__)`. `Task.logs` — `JSONB default=[]`, перезаписывается целиком через `task.logs = current_logs` (не append), структура не типизирована
- JSONB-поля: `Task.serp_data`, `Task.outline`, `Task.step_results`, `Task.serp_config`, `Task.logs`, `SiteProject.serp_config`, `SiteProject.project_keywords`, `SiteProject.legal_template_map`, `SiteProject.logs`
- Нет: `pyproject.toml`, `.github/workflows/`, `.pre-commit-config.yaml`, `ruff`/`black`/`mypy` конфигов
- Alembic работает штатно, миграции в `alembic/versions/`

---

## Порядок реализации (последовательный, можно коммитить отдельно)

| #   | Шаг                                                                                            | Дней | Зависимости |
| --- | ---------------------------------------------------------------------------------------------- | ---- | ----------- |
| 1.1 | Инструментарий: `pyproject.toml`, `ruff`, pre-commit                                           | 0.5  | —           |
| 1.2 | Pydantic-схемы: создать `app/schemas/` и перенести туда request/response-классы + JSONB-модели | 2    | 1.1         |
| 1.3 | Тестовая инфраструктура: `conftest.py`, тестовая БД, фабрики                                   | 1.5  | 1.2         |
| 1.4 | API-тесты happy-path по 14 роутерам                                                            | 3–4  | 1.3         |
| 1.5 | Smoke-тест пайплайна + тест Celery-таска с моками                                              | 2    | 1.3         |
| 1.6 | Структурированное логирование (structlog)                                                      | 1.5  | 1.1         |
| 1.7 | Миграция `Task.logs` → `log_events` с лимитом и типизацией                                     | 1    | 1.2, 1.6    |
| 1.8 | CI: GitHub Actions workflow                                                                    | 0.5  | 1.4         |

**Итого:** ~12 дней чистой работы = 2.5 недели с запасом.

---

## 1.1. Инструментарий

### Создать `pyproject.toml`

В корне проекта рядом с [requirements.txt](requirements.txt). Назначение — единая конфигурация для `ruff`, `pytest`, `mypy` (точечно).

```toml
[tool.ruff]
line-length = 110
target-version = "py311"
extend-exclude = ["alembic/versions", "frontend"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]
ignore = ["E501"]  # длинные строки ловим форматтером

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["B", "SIM"]
"scripts/*" = ["B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
filterwarnings = ["ignore::DeprecationWarning"]
addopts = "-ra --strict-markers"
markers = [
    "integration: tests that hit a real DB",
    "slow: tests > 1s",
]

[tool.mypy]
python_version = "3.11"
files = ["app/services/llm.py", "app/services/json_parser.py", "app/services/meta_parser.py"]
strict = true
ignore_missing_imports = true
```

### Добавить в [requirements.txt](requirements.txt) dev-зависимости

Либо вынести в `requirements-dev.txt` — предпочтительнее, не раздувать прод-образ:

```
# requirements-dev.txt
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=4.1
httpx>=0.27
factory-boy>=3.3
freezegun>=1.4
ruff>=0.4
pre-commit>=3.7
structlog>=24.1
```

### `.pre-commit-config.yaml` в корне

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

**Действия:** `pre-commit install`, `ruff check --fix app/`, `ruff format app/`. Первый прогон даст большой diff — закоммитить отдельно (`style: initial ruff pass`).

**DoD:** `pre-commit run --all-files` проходит. `pytest` запускается (пусть и со старыми тестами).

---

## 1.2. Pydantic-схемы: создать `app/schemas/`

### Почему первым делом

Сейчас Pydantic-классы (SerpConfig, TaskCreate и т.д.) живут внутри роутеров. Для тестов API их будут нужны в фикстурах — без выноса получим циклические импорты и дубли. Плюс именно Pydantic-модели закроют "fix parsing" баги из недавней истории (схема ловит мусор на входе).

### Структура

```
app/schemas/
  __init__.py
  common.py          # общие типы, Enums, дженерики ответов
  task.py            # TaskCreate, TaskResponse, TaskListItem, UpdateStepResult
  project.py         # ProjectCreate, ProjectUpdate, ProjectResponse
  site.py            # SiteCreate, SiteResponse
  blueprint.py       # BlueprintCreate, BlueprintPageCreate, ...
  author.py          # AuthorCreate, AuthorResponse
  prompt.py          # PromptCreate, PromptResponse
  template.py        # TemplateCreate, TemplateResponse
  legal_page.py      # LegalPageTemplate schemas
  # --- JSONB-контракты (самое важное) ---
  serp_config.py     # SerpConfig (перенести из app/api/tasks.py)
  step_result.py     # StepResult, StepStatus enum, PipelinePlan
  log_event.py       # LogEvent, LogLevel enum
  project_keywords.py # ProjectKeywords (raw, clustered, unassigned)
```

### JSONB-контракты — примеры (писать с нуля по текущему коду)

**`app/schemas/step_result.py`:**

```python
from enum import Enum
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field

class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"

class StepResult(BaseModel):
    status: StepStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    output: Any = None                   # произвольный JSON-вывод шага
    error: str | None = None
    attempts: int = 1

class PipelinePlan(BaseModel):
    steps: list[str]
    preset: str | None = None
    resolved_at: datetime

class TaskStepResults(BaseModel):
    """Обёртка над всем Task.step_results JSONB."""
    pipeline_plan: PipelinePlan | None = Field(default=None, alias="_pipeline_plan")
    steps: dict[str, StepResult | list[StepResult]] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
```

**`app/schemas/log_event.py`:**

```python
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"

class LogEvent(BaseModel):
    ts: datetime
    level: LogLevel
    event: str                    # короткий machine-readable: "serp_fetched", "llm_call", "step_failed"
    step: str | None = None
    message: str | None = None    # человекочитаемое
    duration_ms: int | None = None
    extra: dict = {}              # произвольные поля
```

### Хелперы валидации

`app/schemas/jsonb_adapter.py` — функции чтения/записи JSONB-полей с валидацией:

```python
from pydantic import TypeAdapter
from app.schemas.step_result import TaskStepResults
from app.schemas.log_event import LogEvent

_step_results_adapter = TypeAdapter(TaskStepResults)
_log_events_adapter = TypeAdapter(list[LogEvent])

def read_step_results(raw: dict | None) -> TaskStepResults:
    return _step_results_adapter.validate_python(raw or {})

def write_step_results(obj: TaskStepResults) -> dict:
    return obj.model_dump(by_alias=True, mode="json", exclude_none=True)

def read_log_events(raw: list | None) -> list[LogEvent]:
    return _log_events_adapter.validate_python(raw or [])

def append_log_event(raw: list | None, event: LogEvent, max_len: int = 500) -> list[dict]:
    events = read_log_events(raw)
    events.append(event)
    if len(events) > max_len:
        events = events[-max_len:]
    return [e.model_dump(mode="json") for e in events]
```

### Перенос классов из роутеров

1. В [app/api/tasks.py](app/api/tasks.py) найти все `class XxxRequest(BaseModel):` / `class XxxResponse(BaseModel):` — перенести в `app/schemas/task.py`, в роутере оставить `from app.schemas.task import TaskCreate, ...`
2. Повторить для [app/api/projects.py](app/api/projects.py), [app/api/sites.py](app/api/sites.py) и других
3. Запустить `pytest` (старые тесты) — не должно сломаться, так как импорт-поверхность та же

**DoD:**
- Роутеры не содержат определений Pydantic-классов (grep `class.*BaseModel` в `app/api/` → пусто)
- `app/schemas/` импортируется без ошибок
- Все 5 ключевых JSONB-полей имеют свои схемы

---

## 1.3. Тестовая инфраструктура

### `tests/conftest.py`

Главная цель — **реальная тестовая БД**, а не mock. При 15–20 проектах/день прод-нагрузка низкая, но тесты на моках маскируют баги ORM/миграций.

```python
# tests/conftest.py
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
from alembic.config import Config
from alembic import command

from app.database import Base, get_db
from app.main import app
from app.config import settings

TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/seo_test")

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DB_URL, future=True)
    # Накатить все миграции через alembic — ловим проблемы миграций в тестах
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(cfg, "head")
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture()
def db_session(db_engine):
    """Транзакционная изоляция — каждый тест откатывается."""
    connection = db_engine.connect()
    trans = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()

@pytest.fixture()
async def client(db_session):
    def _override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture()
def api_key_headers():
    return {"X-API-Key": settings.API_KEY or ""}
```

### Фабрики: `tests/factories.py`

Использовать `factory_boy` вместо MagicMock. Пример на `Task`:

```python
import factory
from uuid import uuid4
from app.models.task import Task
from app.models.site import Site

class SiteFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Site
        sqlalchemy_session_persistence = "flush"
    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"site-{n}")
    # ...

class TaskFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Task
        sqlalchemy_session_persistence = "flush"
    id = factory.LazyFunction(uuid4)
    main_keyword = "test casino"
    country = "DE"
    language = "de"
    page_type = "review"
    status = "pending"
    target_site = factory.SubFactory(SiteFactory)
```

В `conftest.py` прокидывать `db_session` в фабрики через autouse-фикстуру:

```python
@pytest.fixture(autouse=True)
def _bind_factories(db_session):
    for factory_cls in [SiteFactory, TaskFactory, ...]:
        factory_cls._meta.sqlalchemy_session = db_session
```

### Тестовая БД в docker-compose

Добавить в [docker-compose.yml](docker-compose.yml) сервис `db-test` на порту 5433 (или отдельную БД `seo_test` в том же Postgres). Документировать в `README.md`:

```bash
createdb seo_test -h localhost -U postgres
TEST_DATABASE_URL=postgresql://... pytest
```

**DoD:**
- `pytest tests/` проходит на чистой БД
- `conftest.py` поднимает миграции и откатывает транзакции между тестами
- Фабрики работают для Task, Site, Project, Blueprint, Prompt, Author, Template

---

## 1.4. API-тесты happy-path

### Структура

```
tests/api/
  test_health.py
  test_tasks_api.py
  test_projects_api.py
  test_sites_api.py
  test_blueprints_api.py
  test_prompts_api.py
  test_templates_api.py
  test_authors_api.py
  test_legal_pages_api.py
  test_articles_api.py
  test_dashboard_api.py
  test_settings_api.py
  test_logs_api.py
```

### Шаблон теста (CRUD-роутер)

```python
# tests/api/test_sites_api.py
import pytest
from tests.factories import SiteFactory

@pytest.mark.asyncio
async def test_list_sites_empty(client, api_key_headers):
    r = await client.get("/api/sites/", headers=api_key_headers)
    assert r.status_code == 200
    assert r.json() == []

@pytest.mark.asyncio
async def test_create_site(client, api_key_headers):
    r = await client.post("/api/sites/", json={"name": "X", "domain": "x.com"}, headers=api_key_headers)
    assert r.status_code == 201
    assert r.json()["name"] == "X"

@pytest.mark.asyncio
async def test_get_site_404(client, api_key_headers):
    r = await client.get("/api/sites/00000000-0000-0000-0000-000000000000", headers=api_key_headers)
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_create_site_validation_error(client, api_key_headers):
    r = await client.post("/api/sites/", json={}, headers=api_key_headers)
    assert r.status_code == 422
```

### Что покрыть (минимум по роутеру)

- `GET /` (пустой список → 200)
- `POST /` (успех → 200/201)
- `POST /` (невалидный JSON → 422)
- `GET /{id}` (не найден → 404)
- Если есть `PUT`/`PATCH`: happy-path
- Если есть `DELETE`: успех + 404 на повтор

Для `tasks.py` и `projects.py` (гигантские роутеры) — по 8–12 тестов каждый, включая:
- Запуск задачи (`POST /start`) с моком Celery (`apply_async` → заглушка)
- Обновление шага (`PUT /{task_id}/steps`)
- Фильтры списков (status, site_id, search)
- Архивация/удаление (recently fixed → нужны регрессионные тесты!)

### Моки внешних сервисов

В `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def _mock_external(monkeypatch):
    monkeypatch.setattr("app.services.llm.generate_text", lambda *a, **kw: '{"ok": true}')
    monkeypatch.setattr("app.services.serp.fetch_serp_data", lambda *a, **kw: {"results": []})
    monkeypatch.setattr("app.services.scraper.scrape_urls", lambda urls, *a, **kw: {u: "" for u in urls})
    # Celery — работать только eager
    from app.workers.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
```

**DoD:**
- `pytest tests/api/ --cov=app/api` → coverage ≥ 70% на `app/api/`
- Тест archive/delete для проектов/задач есть (регрессия для последних коммитов)

---

## 1.5. Smoke-тест пайплайна + Celery-таска

### Тест пайплайна

```python
# tests/services/test_pipeline_smoke.py
from tests.factories import TaskFactory
from app.services.pipeline import run_pipeline  # или как называется точка входа

def test_pipeline_runs_single_step(db_session, monkeypatch):
    task = TaskFactory(step_results={})
    db_session.flush()
    # замокать LLM, SERP, scraper — fixture autouse уже делает
    run_pipeline(db_session, str(task.id), steps=["serp_fetch"])
    db_session.refresh(task)
    assert task.step_results["serp_fetch"]["status"] == "completed"
    assert task.status in ("processing", "completed")
```

### Тест Celery-таска

```python
# tests/workers/test_tasks.py
from app.workers.tasks import process_generation_task
from tests.factories import TaskFactory

def test_process_generation_task_success(db_session, monkeypatch):
    task = TaskFactory()
    db_session.commit()
    result = process_generation_task.apply(args=[str(task.id)]).get()
    db_session.refresh(task)
    assert task.status in ("completed", "failed")  # главное — не упал и статус проставился
```

Если сейчас Celery-таск требует Redis — использовать `task_always_eager=True` (см. 1.4).

**DoD:**
- Pipeline smoke-тест зелёный
- Celery-таск запускается в eager-режиме без Redis

---

## 1.6. Структурированное логирование (structlog)

### Почему structlog, а не loguru

- `structlog` даёт плотную интеграцию со стандартным `logging` (не надо переписывать существующий код — `logger = logging.getLogger(__name__)` остаётся)
- JSON-рендер из коробки
- Контекст-переменные (`bind_contextvars`) — можно "прицепить" `task_id` в начале обработки, и он автоматически попадёт во все последующие логи этого запроса/задачи

### Конфигурация: `app/logging_config.py`

```python
import logging
import structlog

def configure_logging(json_logs: bool = True, level: str = "INFO") -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    structlog.configure(
        processors=shared_processors + [
            structlog.processors.JSONRenderer() if json_logs
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Перенаправить стандартный logging в structlog
    handler = logging.StreamHandler()
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=shared_processors,
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
```

### Интеграция

**В [app/main.py](app/main.py):**

```python
from app.logging_config import configure_logging
configure_logging(json_logs=settings.LOG_JSON, level=settings.LOG_LEVEL)
```

**В [app/workers/celery_app.py](app/workers/celery_app.py):** то же самое при старте воркера (`worker_process_init` сигнал).

**Binding контекста в пайплайне:**

```python
import structlog
log = structlog.get_logger()

# В начале обработки задачи:
structlog.contextvars.bind_contextvars(task_id=str(task.id), project_id=str(task.project_id))
log.info("pipeline_started", steps=plan.steps)

# В конце:
structlog.contextvars.clear_contextvars()
```

### Настройки в `app/config.py`

```python
LOG_JSON: bool = True
LOG_LEVEL: str = "INFO"
```

**DoD:**
- Запуск `uvicorn app.main:app` — логи в JSON (одна строка = один event, есть `task_id`, `ts`, `level`)
- Тест в [tests/test_logging.py](tests/test_logging.py): вызвать logger, распарсить stdout как JSON

---

## 1.7. Миграция `Task.logs` → `log_events`

### Зачем

Сейчас `task.logs = current_logs` **перезаписывает** весь JSONB-массив при каждом событии. Это:
- медленно (JSONB-update на мегабайт)
- теряет хвост при конкурентных апдейтах
- колонка растёт без ограничений

### Alembic-миграция

Новый файл `alembic/versions/xxxx_rename_logs_to_log_events.py`:

```python
def upgrade():
    # Добавить новую колонку
    op.add_column("tasks", sa.Column("log_events", postgresql.JSONB(), server_default="[]", nullable=False))
    op.add_column("site_projects", sa.Column("log_events", postgresql.JSONB(), server_default="[]", nullable=False))
    # Скопировать только последние 500 записей (из старой колонки logs)
    op.execute("""
        UPDATE tasks
        SET log_events = COALESCE(
            (SELECT jsonb_agg(e) FROM (
                SELECT * FROM jsonb_array_elements(logs)
                OFFSET GREATEST(jsonb_array_length(logs) - 500, 0)
            ) e),
            '[]'::jsonb
        )
        WHERE logs IS NOT NULL;
    """)
    # Аналогично для site_projects
    op.drop_column("tasks", "logs")
    op.drop_column("site_projects", "logs")

def downgrade():
    op.add_column("tasks", sa.Column("logs", postgresql.JSONB(), server_default="[]"))
    op.execute("UPDATE tasks SET logs = log_events")
    op.drop_column("tasks", "log_events")
    # аналогично
```

### Обновить модели

[app/models/task.py](app/models/task.py):
```python
log_events = Column(JSONB, nullable=False, default=list)
```

### Обновить места записи

Найти grep `task.logs` / `project.logs` — заменить на `append_log_event`:

```python
from app.schemas.jsonb_adapter import append_log_event
from app.schemas.log_event import LogEvent, LogLevel

task.log_events = append_log_event(
    task.log_events,
    LogEvent(ts=datetime.utcnow(), level=LogLevel.info, event="serp_fetched", step="serp_fetch"),
    max_len=500,
)
```

**Можно сделать sqlalchemy-хелпер на уровне модели:**

```python
# app/models/task.py
def push_log(self, event: str, level: str = "info", **extra):
    self.log_events = append_log_event(self.log_events, LogEvent(
        ts=datetime.utcnow(), level=level, event=event, extra=extra,
    ))
```

Тогда в коде: `task.push_log("serp_fetched", step="serp_fetch", duration_ms=1234)`.

### Фронтенд

В [frontend/src/pages/TaskDetail](frontend/src/pages/) и [ProjectDetail](frontend/src/pages/) заменить чтение `task.logs` на `task.log_events`. Проверить формат отображения (было просто `{level, message}`, станет structured).

**DoD:**
- Миграция применяется и откатывается
- Старые задачи из прода сохранили последние 500 логов (проверить на проде после деплоя)
- Фронтенд показывает логи корректно
- Нет grep-совпадений `\.logs\s*=` по `app/` (кроме `log_events`)

---

## 1.8. CI: GitHub Actions

### `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: seo_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: "pip" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check app/
      - run: ruff format --check app/
      - run: pytest --cov=app --cov-report=term-missing
        env:
          TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/seo_test
          REDIS_URL: redis://localhost:6379/0
          API_KEY: test
          OPENROUTER_API_KEY: test

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm", cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
```

**DoD:** PR в main запускает workflow, он зелёный.

---

## Критические файлы для модификации (сводно)

| Файл                                                      | Что делаем                                         |
| --------------------------------------------------------- | -------------------------------------------------- |
| [pyproject.toml](pyproject.toml)                          | создать                                            |
| [requirements-dev.txt](requirements-dev.txt)              | создать                                            |
| [.pre-commit-config.yaml](.pre-commit-config.yaml)        | создать                                            |
| [.github/workflows/ci.yml](.github/workflows/)            | создать                                            |
| [app/schemas/](app/schemas/)                              | новая директория, ~12 файлов                       |
| [app/api/tasks.py](app/api/tasks.py)                      | убрать Pydantic-классы, импорт из schemas          |
| [app/api/projects.py](app/api/projects.py)                | то же                                              |
| [app/api/sites.py](app/api/sites.py)                      | то же                                              |
| [app/api/*.py](app/api/)                                  | то же (остальные 11 роутеров)                      |
| [app/logging_config.py](app/logging_config.py)            | создать                                            |
| [app/main.py](app/main.py)                                | `configure_logging()` при старте                   |
| [app/workers/celery_app.py](app/workers/celery_app.py)    | `configure_logging()` в worker init                |
| [app/models/task.py](app/models/task.py)                  | `logs` → `log_events`, метод `push_log`            |
| [app/models/project.py](app/models/project.py)            | то же                                              |
| [app/services/pipeline.py](app/services/pipeline.py)      | заменить `task.logs = ...` на `task.push_log(...)` |
| [alembic/versions/xxxx_rename_logs.py](alembic/versions/) | создать миграцию                                   |
| [tests/conftest.py](tests/conftest.py)                    | создать                                            |
| [tests/factories.py](tests/factories.py)                  | создать                                            |
| [tests/api/*](tests/)                                     | создать 13 файлов                                  |
| [tests/services/test_pipeline_smoke.py](tests/)           | создать                                            |
| [tests/workers/test_tasks.py](tests/)                     | создать                                            |
| [docker-compose.yml](docker-compose.yml)                  | опционально — тестовая БД                          |
| [README.md](README.md)                                    | секция "Running tests"                             |

---

## Переиспользуемые утилиты (не дублировать в тестах)

- [app/services/json_parser.py](app/services/json_parser.py) — `clean_and_parse_json` (в тестах моков LLM отдавать валидный JSON и дёргать этот парсер)
- [app/services/meta_parser.py](app/services/meta_parser.py) — `extract_meta_from_parsed`
- [app/api/deps.py](app/api/deps.py) — `get_db`, `verify_api_key` (переиспользовать через dependency_override)

---

## Верификация Этапа 1 (как понять, что закончил)

| #   | Команда                                                                | Ожидаемый результат                                                         |
| --- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1   | `ruff check app/`                                                      | 0 ошибок                                                                    |
| 2   | `pre-commit run --all-files`                                           | all passed                                                                  |
| 3   | `grep -rn "class.*BaseModel" app/api/`                                 | пусто                                                                       |
| 4   | `pytest --cov=app/api`                                                 | coverage ≥ 70%                                                              |
| 5   | `pytest --cov=app/services`                                            | coverage ≥ 50%                                                              |
| 6   | `pytest tests/services/test_pipeline_smoke.py`                         | green                                                                       |
| 7   | `pytest tests/workers/`                                                | green                                                                       |
| 8   | `uvicorn app.main:app` + dummy request                                 | в stdout одна JSON-строка на событие, есть поле `task_id` при работе задачи |
| 9   | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` | без ошибок                                                                  |
| 10  | `grep -rn "\.logs\s*=" app/` (кроме log_events)                        | пусто                                                                       |
| 11  | Открыть фронт, создать задачу, посмотреть Logs в TaskDetail            | отображаются `log_events` корректно                                         |
| 12  | GitHub Actions на PR                                                   | green                                                                       |

Если все 12 пунктов зелёные — Этап 1 завершён, можно идти в Этап 2 (декомпозиция пайплайна).

---

## Риски и что может пойти не так

1. **Тесты на реальной БД замедляют CI.** Mitigation: транзакционная изоляция (транзакция откатывается), `session`-scope для engine → миграции накатываются один раз. Ожидаемое время всего pytest ≤ 2 мин.

2. **Миграция log_events может упасть на больших таблицах.** Mitigation: при деплое в прод — сначала `pg_dump` таблицы `tasks`, потом миграция. Обрезание до 500 записей сделано именно чтобы миграция была быстрой.

3. **Pydantic-валидация step_results ломает прод-задачи с "грязным" JSONB.** Mitigation: на первом этапе валидация **только при записи** (новые записи). Чтение — с `try/except`, fallback на пустую структуру. Через 2 недели, когда все новые задачи пишут валидный JSON, включить строгое чтение.

4. **structlog + Celery: контекст-переменные могут течь между задачами.** Mitigation: обязательный `clear_contextvars()` в `finally` в начале/конце каждого Celery-таска.

5. **Соло-разработчик не дойдёт до конца этапа.** Mitigation: каждый подпункт (1.1–1.8) — отдельный PR/коммит, которые приносят пользу сами по себе. Можно остановиться после 1.4 и иметь уже работающую тестовую сетку.
