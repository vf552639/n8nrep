"""Smoke checks for pipeline helpers (uses integration DB when configured)."""

import pytest

from app.services.pipeline import add_log


@pytest.mark.integration
def test_add_log_appends_and_truncates(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    monkeypatch.setattr("app.services.pipeline.settings", type("S", (), {"TEST_MODE": False})())
    from tests.factories import SiteFactory, TaskFactory

    SiteFactory._meta.sqlalchemy_session = db_session
    TaskFactory._meta.sqlalchemy_session = db_session

    site = SiteFactory()
    db_session.flush()
    task = TaskFactory(target_site_id=site.id, log_events=[])
    db_session.flush()

    for i in range(3):
        add_log(db_session, task, f"msg-{i}", step="test")
    db_session.refresh(task)
    assert len(task.log_events) == 3
    assert task.log_events[-1]["msg"] == "msg-2"
