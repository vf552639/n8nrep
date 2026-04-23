from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# engine for PostgreSQL via psycopg2 — pool tuning for Supabase/Supavisor (idle-in-transaction, stale conns)
engine = create_engine(
    settings.SUPABASE_DB_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    # Worker pipeline commits large JSONB (step_results); 60s server-side timeout caused
    # OperationalError on heavy updates — align with task53 E.2 (10 minutes).
    connect_args={"options": "-c statement_timeout=600000"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
