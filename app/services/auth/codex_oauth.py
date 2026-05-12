from __future__ import annotations

import json
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)


def auth_path() -> Path:
    from app.config import settings
    return Path(settings.OPENAI_OAUTH_DIR) / "auth.json"


def read_status() -> dict:
    from app.config import settings

    p = auth_path()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            toks = data.get("tokens") or {}
            if toks.get("access_token"):
                return {
                    "logged_in": True,
                    "method": "oauth",
                    "account_id": toks.get("account_id"),
                }
        except Exception as e:
            _logger.warning("codex_status_read_failed: %s", e)

    if settings.OPENAI_API_KEY:
        return {"logged_in": True, "method": "api_key", "account_id": None}

    return {"logged_in": False, "method": None, "account_id": None}


def logout() -> None:
    p = auth_path()
    if p.exists():
        p.unlink()
