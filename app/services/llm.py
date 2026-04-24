import json
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings

_openai_client = None


def timeout_for_model(model: str) -> int:
    raw = (settings.LLM_MODEL_TIMEOUTS or "").strip()
    if raw:
        for pair in raw.split(","):
            k, _, v = pair.partition("=")
            if k.strip() == model and v.strip().isdigit():
                return int(v)
    return settings.LLM_REQUEST_TIMEOUT


def fallbacks_for_model(model: str) -> list[str]:
    raw = (settings.LLM_MODEL_FALLBACKS or "").strip()
    if not raw:
        return []
    for pair in raw.split(","):
        k, _, v = pair.partition("=")
        if k.strip() != model:
            continue
        out: list[str] = []
        for fb in v.split("|"):
            t = fb.strip()
            if not t or t == model:
                continue
            if t not in out:
                out.append(t)
        return out
    return []


def get_openai_client() -> OpenAI:
    """Returns an OpenAI client configured for OpenRouter (Singleton)"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
    return _openai_client


def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = settings.DEFAULT_MODEL,
    temperature: float = 0.7,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    max_retries: int = 2,
    response_format: dict[str, str] | None = None,
    timeout: int | None = None,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> tuple[str, float, str, dict[str, Any] | None]:
    """
    Generic LLM call with retry policy. Returns (generated_text, estimated_cost, actual_model, usage_or_none).
    """
    # Imported here to avoid circular import: app.services.pipeline.__init__ imports generate_text from this module.
    from app.services.pipeline.errors import InsufficientCreditsError

    effective_timeout = timeout if timeout is not None else timeout_for_model(model)
    client = get_openai_client()

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    last_error = None
    retries = 0
    credit_downscales = 0
    while retries < max_retries:
        attempt_start = time.monotonic()
        print(f"[LLM] Attempt {retries + 1}/{max_retries}, model={model}, timeout={effective_timeout}s")
        try:
            if progress_callback:
                progress_callback(
                    "request_start",
                    {
                        "attempt": retries + 1,
                        "max_retries": max_retries,
                        "model": model,
                        "max_tokens": max_tokens,
                        "timeout": effective_timeout,
                    },
                )
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "extra_headers": {
                    "HTTP-Referer": "https://example.com",  # Update logically later
                    "X-Title": "SEO-Generator",
                },
                "timeout": effective_timeout,
            }
            if frequency_penalty is not None:
                kwargs["frequency_penalty"] = frequency_penalty
            if presence_penalty is not None:
                kwargs["presence_penalty"] = presence_penalty
            if top_p is not None:
                kwargs["top_p"] = top_p
            if max_tokens is not None and max_tokens > 0:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format

            fallbacks = fallbacks_for_model(model)
            if fallbacks:
                models_list = [model, *fallbacks]
                kwargs["extra_body"] = {"models": models_list}

            raw_response = client.chat.completions.with_raw_response.create(**kwargs)
            response = raw_response.parse()

            cost = 0.0
            usage_info: dict[str, Any] | None = None

            try:
                raw_data = json.loads(raw_response.text)
                if "usage" in raw_data:
                    usage_raw = raw_data["usage"]
                    cost = float(usage_raw.get("cost", 0.0))

                    prompt_details = usage_raw.get("prompt_tokens_details", {}) or {}
                    completion_details = usage_raw.get("completion_tokens_details", {}) or {}

                    usage_info = {
                        "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                        "completion_tokens": usage_raw.get("completion_tokens", 0),
                        "total_tokens": usage_raw.get("total_tokens", 0),
                        "cached_tokens": prompt_details.get("cached_tokens", 0),
                        "reasoning_tokens": completion_details.get("reasoning_tokens", 0),
                    }
            except Exception:
                pass

            if cost == 0.0:
                openrouter_cost = raw_response.headers.get("x-openrouter-cost")
                if openrouter_cost:
                    try:
                        cost = float(openrouter_cost)
                    except (ValueError, TypeError):
                        pass

            if cost == 0.0 and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                if "gpt-4o-mini" in model:
                    cost = (prompt_tokens * 0.15 / 1000000) + (completion_tokens * 0.60 / 1000000)
                elif "gemini-3" in model or "gemini-2.5" in model:
                    cost = (prompt_tokens * 0.075 / 1000000) + (completion_tokens * 0.30 / 1000000)
                else:
                    cost = (prompt_tokens * 0.1 / 1000000) + (completion_tokens * 0.5 / 1000000)

            if usage_info is None and response.usage:
                usage_info = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            actual_model = getattr(response, "model", None) or model
            if progress_callback:
                progress_callback(
                    "response_received",
                    {
                        "attempt": retries + 1,
                        "cost": cost,
                        "usage": usage_info or {},
                        "model": actual_model,
                    },
                )
            elapsed = time.monotonic() - attempt_start
            print(f"[LLM] Response OK in {elapsed:.1f}s, model={actual_model}, tokens={usage_info}")
            return response.choices[0].message.content, cost, actual_model, usage_info

        except InsufficientCreditsError:
            raise
        except Exception as e:
            last_error = str(e)
            error_msg = str(e)
            elapsed = time.monotonic() - attempt_start
            status_code = getattr(e, "status_code", None)
            is_402 = status_code == 402 or (
                "402" in error_msg
                and ("payment required" in error_msg.lower() or "can only afford" in error_msg.lower())
            )

            # OpenRouter 402: downscale max_tokens when provider reports an affordable ceiling
            if (
                is_402
                and "can only afford" in error_msg.lower()
                and max_tokens is not None
                and max_tokens > 0
            ):
                m = re.search(r"can only afford\s+(\d+)", error_msg, re.IGNORECASE)
                if m:
                    affordable = int(m.group(1))
                    new_mt = affordable - 256
                    if affordable < max_tokens and new_mt >= 1024 and new_mt < max_tokens:
                        credit_downscales += 1
                        if credit_downscales > 20:
                            raise InsufficientCreditsError(
                                "OpenRouter 402: exhausted max_tokens downscale attempts "
                                f"(last max_tokens={max_tokens}). Last error: {error_msg}"
                            ) from e
                        old_mt = max_tokens
                        max_tokens = new_mt
                        print(
                            f"[LLM] OpenRouter 402: downscaling max_tokens {old_mt} -> {max_tokens} "
                            f"(affordable={affordable}, margin=256); retrying immediately."
                        )
                        if progress_callback:
                            progress_callback(
                                "max_tokens_downscale",
                                {
                                    "attempt": retries + 1,
                                    "max_retries": max_retries,
                                    "old_max_tokens": old_mt,
                                    "new_max_tokens": max_tokens,
                                    "affordable": affordable,
                                    "error": error_msg,
                                },
                            )
                        continue

            if is_402:
                raise InsufficientCreditsError(
                    f"Insufficient OpenRouter credits or max_tokens cannot be adjusted: {error_msg}"
                ) from e

            print(f"[LLM] Error after {elapsed:.1f}s (Attempt {retries + 1}/{max_retries}): {error_msg}")
            sleep_seconds = 5
            reason = "unknown"
            is_timeout = (
                isinstance(e, (httpx.TimeoutException, TimeoutError)) or "timeout" in error_msg.lower()
            )

            # Rate limit or server error logic
            if "429" in error_msg or "rate limit" in error_msg.lower():
                reason = "rate_limit"
                sleep_seconds = 60 * (retries + 1)  # Exponential backoff: 60s, 120s, 180s
            elif "502" in error_msg or "504" in error_msg or is_timeout:
                reason = "upstream_timeout_or_gateway"
                sleep_seconds = 5 * (retries + 1)  # 5s, 10s
            if progress_callback:
                progress_callback(
                    "retry_wait",
                    {
                        "attempt": retries + 1,
                        "max_retries": max_retries,
                        "reason": reason,
                        "sleep_seconds": sleep_seconds,
                        "error": error_msg,
                        "is_timeout": is_timeout,
                    },
                )
            time.sleep(sleep_seconds)

            retries += 1

    raise Exception(
        f"LLM Generation failed after {max_retries} attempts. Model: {model}. Last error: {last_error}"
    )
