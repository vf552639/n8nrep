"""Build OpenRouter / generate_text sampling kwargs from Prompt + optional test overrides."""
from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.prompt import Prompt


def llm_sampling_kwargs_from_prompt(
    prompt: "Prompt",
    *,
    temperature_enabled: Optional[bool] = None,
    temperature: Optional[float] = None,
    frequency_penalty_enabled: Optional[bool] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty_enabled: Optional[bool] = None,
    presence_penalty: Optional[float] = None,
    top_p_enabled: Optional[bool] = None,
    top_p: Optional[float] = None,
    max_tokens_enabled: Optional[bool] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Mirrors pipeline behavior: when *_enabled is False, stored values are ignored for the API call
    and defaults (0.7 / 0 / 1.0 / no max_tokens) are used.
    Optional override args come from prompt test UI (unsaved edits); None means use prompt row.
    """
    te = (
        temperature_enabled
        if temperature_enabled is not None
        else bool(getattr(prompt, "temperature_enabled", False))
    )
    tval = prompt.temperature if temperature is None else temperature
    if tval is None:
        tval = 0.7
    eff_temp = float(tval) if te else 0.7

    fe = (
        frequency_penalty_enabled
        if frequency_penalty_enabled is not None
        else bool(getattr(prompt, "frequency_penalty_enabled", False))
    )
    fval = prompt.frequency_penalty if frequency_penalty is None else frequency_penalty
    if fval is None:
        fval = 0.0
    eff_freq = float(fval) if fe else 0.0

    pe = (
        presence_penalty_enabled
        if presence_penalty_enabled is not None
        else bool(getattr(prompt, "presence_penalty_enabled", False))
    )
    pval = prompt.presence_penalty if presence_penalty is None else presence_penalty
    if pval is None:
        pval = 0.0
    eff_pres = float(pval) if pe else 0.0

    tpe = top_p_enabled if top_p_enabled is not None else bool(getattr(prompt, "top_p_enabled", False))
    tpval = prompt.top_p if top_p is None else top_p
    if tpval is None:
        tpval = 1.0
    eff_top_p = float(tpval) if tpe else 1.0

    mte = (
        max_tokens_enabled
        if max_tokens_enabled is not None
        else bool(getattr(prompt, "max_tokens_enabled", False))
    )
    mt = prompt.max_tokens if max_tokens is None else max_tokens

    out: Dict[str, Any] = {
        "temperature": eff_temp,
        "frequency_penalty": eff_freq,
        "presence_penalty": eff_pres,
        "top_p": eff_top_p,
    }
    if mte and mt is not None and mt > 0:
        out["max_tokens"] = int(mt)
    return out


def format_llm_params_log_line(agent_name: str, prompt: "Prompt", kwargs: Dict[str, Any]) -> str:
    """Human-readable log line for diagnostics (matches task21 spec)."""
    mt = kwargs.get("max_tokens", "auto")
    return (
        f"[{agent_name}] LLM params: model={prompt.model}, "
        f"temp={kwargs.get('temperature', 0.7):.1f} ({'custom' if getattr(prompt, 'temperature_enabled', False) else 'default'}), "
        f"max_tokens={mt}, "
        f"freq={kwargs.get('frequency_penalty', 0.0)}, pres={kwargs.get('presence_penalty', 0.0)}, "
        f"top_p={kwargs.get('top_p', 1.0)}"
    )
