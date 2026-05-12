import asyncio
import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.services.project_runner import get_runner_status, launch_project


def test_get_runner_status_returns_dict():
    status = get_runner_status()
    assert "status" in status
    assert "active_projects" in status
    assert isinstance(status["active_projects"], int)


@pytest.mark.asyncio
async def test_launch_project_creates_background_task(monkeypatch):
    called_with = []

    def fake_sync(project_id):
        called_with.append(project_id)

    monkeypatch.setattr("app.services.project_runner._project_sync", fake_sync)
    pid = str(uuid.uuid4())
    await launch_project(pid)
    await asyncio.sleep(0.05)  # let executor finish
    assert pid in called_with
