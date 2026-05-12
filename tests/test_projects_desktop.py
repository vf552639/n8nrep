import os
os.environ["DESKTOP_MODE"] = "true"
os.environ["SQLITE_DB_PATH"] = "/tmp/test_proj_desktop.sqlite"
os.environ["AUTH_DISABLED"] = "true"

import pytest


def test_project_runner_launch_project_importable():
    from app.services.project_runner import launch_project, get_runner_status
    status = get_runner_status()
    assert status["status"] == "ok"
    assert "active_projects" in status


def test_projects_router_imports_without_celery():
    """Verify the projects router can be imported in desktop mode without celery."""
    from app.api.projects import router
    assert router is not None
