from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

_logger = logging.getLogger(__name__)

# Per-million-token pricing (input, output) in USD. Update as OpenAI changes pricing.
_COST_PER_MTOK: dict[str, dict[str, float]] = {
    "gpt-5":         {"input": 5.0,  "output": 15.0},
    "gpt-5-codex":   {"input": 5.0,  "output": 15.0},
    "gpt-5-mini":    {"input": 0.5,  "output": 1.5},
    "gpt-4.1":       {"input": 2.5,  "output": 10.0},
    "o3":            {"input": 15.0, "output": 60.0},
}


def _read_codex_oauth() -> tuple[str, str] | None:
    """Returns (access_token, account_id) if Codex CLI has logged in."""
    from app.config import settings

    auth_path = Path(settings.OPENAI_OAUTH_DIR) / "auth.json"
    if not auth_path.exists():
        return None
    try:
        data = json.loads(auth_path.read_text())
        toks = data.get("tokens") or {}
        access = toks.get("access_token")
        account = toks.get("account_id") or ""
        if access:
            return access, account
    except Exception as e:
        _logger.warning("codex_oauth_read_failed", exc_info=e)
    return None


def _build_client():
    """OpenAI client preferring Codex OAuth, falling back to OPENAI_API_KEY."""
    import openai
    from app.config import settings

    oauth = _read_codex_oauth()
    if oauth is not None:
        token, account_id = oauth
        return openai.OpenAI(
            api_key=token,
            base_url=settings.OPENAI_BASE_URL,
            default_headers={"X-Codex-Account-Id": account_id} if account_id else {},
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )

    if settings.OPENAI_API_KEY:
        return openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )

    raise ValueError(
        "No OpenAI credentials found. Login via Settings → LLM & Auth (Codex tab) "
        "or set OPENAI_API_KEY in .env."
    )


def generate_text_codex(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: int = 600,
    progress_callback: Optional[Callable[[str, dict[str, Any]], None]] = None,
    response_format: Optional[dict[str, str]] = None,
) -> tuple[str, float, str, Optional[dict[str, Any]]]:
    """Call OpenAI (Codex / ChatGPT subscription). Returns (text, cost, model, usage)."""
    client = _build_client()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "timeout": timeout,
    }
    if max_tokens and max_tokens > 0:
        kwargs["max_tokens"] = max_tokens
    if response_format:
        kwargs["response_format"] = response_format

    if progress_callback:
        progress_callback(
            "request_start",
            {"model": model, "max_tokens": max_tokens, "timeout": timeout},
        )

    start = time.monotonic()
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        elapsed = time.monotonic() - start
        _logger.warning("codex_call_failed model=%s elapsed=%.2f error=%s", model, elapsed, e)
        raise

    text = response.choices[0].message.content or ""

    prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0
    total_tokens = (
        getattr(response.usage, "total_tokens", prompt_tokens + completion_tokens) or 0
    )

    cost_table = _COST_PER_MTOK.get(model, {"input": 5.0, "output": 15.0})
    cost = (prompt_tokens / 1_000_000) * cost_table["input"] + (
        completion_tokens / 1_000_000
    ) * cost_table["output"]

    usage_info = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": 0,
    }

    if progress_callback:
        progress_callback(
            "response_received", {"model": model, "cost": cost, "usage": usage_info}
        )

    return text, cost, getattr(response, "model", model) or model, usage_info
