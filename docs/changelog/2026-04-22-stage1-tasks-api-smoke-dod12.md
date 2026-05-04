# 22 апреля 2026 — Этап 1: доводка (tasks API, smoke-тесты, DoD 1.2)

**Дата:** 2026-04-22
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

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
