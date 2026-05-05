from __future__ import annotations

import pytest

from app.api.projects import _validate_serp_config


def test_validate_serp_config_accepts_off_engine() -> None:
    cfg = {"search_engine": "off", "depth": 10, "device": "mobile", "os": "android"}
    assert _validate_serp_config(cfg) == cfg


def test_validate_serp_config_rejects_unknown_engine() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _validate_serp_config({"search_engine": "yahoo"})
    assert exc.value.status_code == 400
