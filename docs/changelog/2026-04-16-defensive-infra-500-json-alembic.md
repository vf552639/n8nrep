# 16 апреля 2026 — Защитная инфраструктура: 500 как JSON, миграции, пул БД, Alembic DDL

**Дата:** 2026-04-16
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

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
