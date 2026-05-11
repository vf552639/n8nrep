from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

if settings.DESKTOP_MODE:
    _sqlite_url = f"sqlite+aiosqlite:///{settings.SQLITE_DB_PATH}"
    async_engine = create_async_engine(_sqlite_url, echo=False)

    # Enable WAL mode for concurrent reads and enforce FK constraints
    @event.listens_for(async_engine.sync_engine, "connect")
    def _set_wal(dbapi_conn, _):
        import warnings
        cursor = dbapi_conn.execute("PRAGMA journal_mode=WAL")
        mode = cursor.fetchone()[0]
        if mode != "wal":
            warnings.warn(f"SQLite WAL mode not activated; got '{mode}'", RuntimeWarning, stacklevel=2)
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    AsyncSessionLocal = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Stub sync engine — should not be used in desktop mode
    engine = None  # type: ignore[assignment]
    SessionLocal = None  # type: ignore[assignment]

else:
    # PostgreSQL engine via psycopg2 — pool tuning for Supabase/Supavisor (idle-in-transaction, stale conns)
    engine = create_engine(
        settings.SUPABASE_DB_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        pool_size=10,
        max_overflow=20,
        pool_timeout=10,
        connect_args={
            # statement_timeout: pipeline commits large JSONB (task53). TCP keepalives: reduce silent drops during long LLM calls (task59).
            "options": "-c statement_timeout=600000",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )
    # expire_on_commit=False: avoid expired ORM attrs triggering lazy SELECTs after mid-LLM commits (task59).
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
    )
    async_engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]


@contextmanager
def db_session():
    """Sync session context — web mode only."""
    if SessionLocal is None:
        raise RuntimeError("Sync db_session() is not available in DESKTOP_MODE; use async_db_session()")
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_db_session():
    """Async session context — desktop mode only."""
    if AsyncSessionLocal is None:
        raise RuntimeError("async_db_session() is not available in web mode; use db_session()")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_db():
    """FastAPI dependency — sync (web mode)."""
    if SessionLocal is None:
        raise RuntimeError("get_db() sync dependency not available in DESKTOP_MODE")
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db():
    """FastAPI dependency — async (desktop mode)."""
    if AsyncSessionLocal is None:
        raise RuntimeError("get_async_db() not available in web mode")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
