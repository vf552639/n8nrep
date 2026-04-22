"""Shared pytest fixtures (optional Postgres integration tests)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()


def _api_test_database_url() -> str:
    """Prefer explicit test URL; fall back to app DB URL (e.g. CI sets SUPABASE_DB_URL)."""
    return TEST_DATABASE_URL or os.getenv("SUPABASE_DB_URL", "").strip()


def _postgres_available(url: str) -> bool:
    if not url:
        return False
    try:
        eng = create_engine(url, future=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_engine():
    """Real Postgres + Alembic head (set TEST_DATABASE_URL to enable)."""
    if not _postgres_available(TEST_DATABASE_URL):
        pytest.skip("Set TEST_DATABASE_URL to a reachable Postgres URL for integration tests.")
    from alembic.config import Config

    from alembic import command

    engine = create_engine(TEST_DATABASE_URL, future=True)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    connection = db_engine.connect()
    trans = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture(scope="session")
def api_db_engine():
    """Postgres at head revision for HTTP API tests (task36 §1.4)."""
    url = _api_test_database_url()
    if not url or not _postgres_available(url):
        pytest.skip(
            "Postgres not reachable for API tests — set TEST_DATABASE_URL or SUPABASE_DB_URL "
            "(e.g. CI postgres or docker-compose profile test)."
        )
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_engine(url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def api_db_session(api_db_engine) -> Session:
    connection = api_db_engine.connect()
    trans = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
async def async_api_client(api_db_session, monkeypatch):
    """httpx AsyncClient against the FastAPI app; DB is a rolled-back transaction."""
    from httpx import ASGITransport, AsyncClient

    from app.config import settings
    from app.database import get_db
    from app.main import app

    monkeypatch.setattr(settings, "API_KEY", "", raising=False)

    def _override_get_db():
        yield api_db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
