from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, Optional

_logger = logging.getLogger(__name__)

_COST_PER_MTOK: dict[str, dict[str, float]] = {
    "sonar":               {"input": 1.0, "output": 1.0},
    "sonar-pro":           {"input": 3.0, "output": 15.0},
    "sonar-reasoning":     {"input": 1.0, "output": 5.0},
    "sonar-deep-research": {"input": 5.0, "output": 25.0},
}


def _build_client():
    import openai
    from app.config import settings
    if not settings.PERPLEXITY_API_KEY:
        raise ValueError(
            "PERPLEXITY_API_KEY is empty. Set it in Settings → Integrations or .env."
        )
    return openai.OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url=settings.PERPLEXITY_BASE_URL,
        timeout=settings.LLM_REQUEST_TIMEOUT,
    )


def generate_text_perplexity(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: int = 600,
    progress_callback: Optional[Callable[[str, dict[str, Any]], None]] = None,
) -> tuple[str, float, str, Optional[dict[str, Any]]]:
    """Call Perplexity chat-completions. Returns (text, cost, actual_model, usage)."""
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

    if progress_callback:
        progress_callback("request_start", {"model": model, "max_tokens": max_tokens})

    start = time.monotonic()
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        _logger.warning(
            "perplexity_call_failed model=%s elapsed=%.2f error=%s",
            model,
            time.monotonic() - start,
            e,
        )
        raise

    text = resp.choices[0].message.content or ""
    prompt_tokens = getattr(resp.usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(resp.usage, "completion_tokens", 0) or 0
    total = getattr(resp.usage, "total_tokens", prompt_tokens + completion_tokens) or 0

    cost_table = _COST_PER_MTOK.get(model, {"input": 1.0, "output": 5.0})
    cost = (prompt_tokens / 1_000_000) * cost_table["input"] + (
        completion_tokens / 1_000_000
    ) * cost_table["output"]

    usage_info = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "cached_tokens": 0,
    }

    if progress_callback:
        progress_callback(
            "response_received", {"model": model, "cost": cost, "usage": usage_info}
        )

    return text, cost, getattr(resp, "model", model) or model, usage_info
