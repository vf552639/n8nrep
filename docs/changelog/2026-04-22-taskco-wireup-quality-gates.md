# 22 апреля 2026 — taskco: wire-up и quality gates

**Дата:** 2026-04-22
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

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
