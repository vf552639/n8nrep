import os
import pytest

os.environ.setdefault("DESKTOP_MODE", "true")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/test_p2_sync.sqlite")
os.environ.setdefault("AUTH_DISABLED", "true")


def test_sync_session_local_available_in_desktop_mode():
    import importlib
    import app.database as db_mod
    import sqlalchemy as sa
    importlib.reload(db_mod)
    assert db_mod.SessionLocal is not None, "SessionLocal must not be None in desktop mode"
    assert db_mod.engine is not None, "engine must not be None in desktop mode"
    with db_mod.SessionLocal() as sess:
        result = sess.execute(sa.text("SELECT 1")).scalar()
        assert result == 1
