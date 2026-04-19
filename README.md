# SEO Content Generator

Backend: FastAPI + Celery + PostgreSQL. Frontend: Vite/React in `frontend/`.

## Running tests

Unit tests (no database):

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -m "not integration"
```

Integration tests (Postgres + Alembic migrations) need `TEST_DATABASE_URL`, for example:

```bash
docker compose --profile test up -d db-test
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/seo_test
pytest -m integration
```

CI runs `pytest -m "not integration"` with minimal env vars; enable integration locally when validating DB migrations.

After pulling changes that include Alembic revisions, run:

```bash
alembic upgrade head
```

## Lint / format (new modules)

```bash
ruff check app/schemas app/logging_config.py app/workers/celery_app.py
ruff format app/schemas app/logging_config.py app/workers/celery_app.py
```
