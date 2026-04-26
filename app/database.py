from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# engine for PostgreSQL via psycopg2 — pool tuning for Supabase/Supavisor (idle-in-transaction, stale conns)
engine = create_engine(
    settings.SUPABASE_DB_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    # statement_timeout: worker pipeline commits large JSONB (task53 E).
    # TCP keepalives: reduce silent drops during long LLM calls without DB traffic (task59).
    connect_args={
        "options": "-c statement_timeout=600000",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)

# expire_on_commit=False: avoid expired ORM attributes triggering lazy SELECTs on a stale
# connection after add_log commits mid-LLM (task59 / Supavisor drops).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

Base = declarative_base()


@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
