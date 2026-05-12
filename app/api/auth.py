from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

router = APIRouter()
_logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https://[^\s]+")
_login_proc: Optional[subprocess.Popen] = None


@router.post("/claude/login")
def start_claude_login() -> dict:
    """Spawn `claude /login`, parse the OAuth URL from stdout, return it."""
    global _login_proc

    if _login_proc is not None and _login_proc.poll() is None:
        _login_proc.kill()
        _login_proc = None

    try:
        proc = subprocess.Popen(
            ["claude", "/login"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        return {"error": "claude CLI not found in PATH. Install it first."}

    _login_proc = proc

    url: Optional[str] = None
    for _ in range(50):
        line = proc.stdout.readline()
        if not line:
            break
        m = _URL_RE.search(line)
        if m:
            url = m.group(0).rstrip(".")
            break

    if not url:
        proc.kill()
        _login_proc = None
        return {"error": "Could not parse login URL from claude CLI output."}

    return {"url": url, "status": "pending"}


@router.get("/claude/status")
def get_claude_status() -> dict:
    """Read ~/.claude/.credentials.json to determine login state."""
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if not creds_path.exists():
        return {"logged_in": False, "email": None}
    try:
        creds = json.loads(creds_path.read_text())
        oauth = creds.get("claudeAiOauth", {})
        token = oauth.get("accessToken", "")
        email = oauth.get("userEmail") or creds.get("userEmail")
        return {"logged_in": bool(token), "email": email}
    except Exception as exc:
        _logger.warning("Could not read claude credentials: %s", exc)
        return {"logged_in": False, "email": None}
