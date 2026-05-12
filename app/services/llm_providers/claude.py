from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Optional

_logger = logging.getLogger(__name__)

_THINKING_BUDGET: dict[str, int] = {
    "low": 0,
    "medium": 5_000,
    "high": 10_000,
    "extra_high": 20_000,
}

_MODELS_WITH_THINKING = {"claude-opus-4-7", "claude-sonnet-4-6"}

_COST_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-opus-4-7":           {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6":         {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
}


def _get_client():
    """Return an Anthropic client using OAuth credentials or ANTHROPIC_API_KEY."""
    import anthropic

    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        try:
            creds = json.loads(creds_path.read_text())
            token = creds.get("claudeAiOauth", {}).get("accessToken", "")
            if token:
                return anthropic.Anthropic(auth_token=token)
        except Exception:
            pass

    from app.config import settings

    if settings.ANTHROPIC_API_KEY:
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    raise ValueError(
        "No Claude credentials found. Login via Settings → LLM & Auth or set ANTHROPIC_API_KEY in .env."
    )


def generate_text_claude(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: Optional[int] = None,
    temperature: float = 0.7,
    effort: str = "low",
    fast_mode: bool = False,
    timeout: int = 600,
    progress_callback: Optional[Callable[[str, dict[str, Any]], None]] = None,
) -> tuple[str, float, str, Optional[dict[str, Any]]]:
    """Call Anthropic API directly with optional extended thinking."""
    client = _get_client()

    thinking_budget = 0 if fast_mode else _THINKING_BUDGET.get(effort, 0)
    use_thinking = thinking_budget > 0 and model in _MODELS_WITH_THINKING

    effective_max_tokens = max_tokens or 4_096
    if use_thinking:
        effective_max_tokens = max(effective_max_tokens, thinking_budget + 1_024)

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": effective_max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    if use_thinking:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        kwargs["temperature"] = 1.0
    else:
        kwargs["temperature"] = temperature

    if progress_callback:
        progress_callback(
            "request_start",
            {"model": model, "effort": effort, "fast_mode": fast_mode, "thinking": use_thinking},
        )

    start = time.monotonic()
    try:
        response = client.messages.create(**kwargs)
    except Exception as e:
        elapsed = time.monotonic() - start
        _logger.warning("Claude SDK error after %.1fs model=%s: %s", elapsed, model, e)
        raise

    text_parts = [block.text for block in response.content if block.type == "text"]
    result_text = "\n".join(text_parts)

    cost_table = _COST_PER_MTOK.get(model, {"input": 3.0, "output": 15.0})
    input_cost = (response.usage.input_tokens / 1_000_000) * cost_table["input"]
    output_cost = (response.usage.output_tokens / 1_000_000) * cost_table["output"]
    cost = input_cost + output_cost

    usage_info: dict[str, Any] = {
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        "cached_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    }

    if progress_callback:
        progress_callback("response_received", {"model": model, "cost": cost, "usage": usage_info})

    return result_text, cost, model, usage_info
