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
    When *_enabled is False, that sampling parameter is omitted from the dict so OpenRouter
    uses provider defaults (no explicit top_p=1.0 / penalty=0 in the request).

    Temperature is always included: 0.7 when disabled (system default), or the stored value when enabled.

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
    eff_freq = float(fval)

    pe = (
        presence_penalty_enabled
        if presence_penalty_enabled is not None
        else bool(getattr(prompt, "presence_penalty_enabled", False))
    )
    pval = prompt.presence_penalty if presence_penalty is None else presence_penalty
    if pval is None:
        pval = 0.0
    eff_pres = float(pval)

    tpe = top_p_enabled if top_p_enabled is not None else bool(getattr(prompt, "top_p_enabled", False))
    tpval = prompt.top_p if top_p is None else top_p
    if tpval is None:
        tpval = 1.0
    eff_top_p = float(tpval)

    mte = (
        max_tokens_enabled
        if max_tokens_enabled is not None
        else bool(getattr(prompt, "max_tokens_enabled", False))
    )
    mt = prompt.max_tokens if max_tokens is None else max_tokens

    out: Dict[str, Any] = {"temperature": eff_temp}
    if fe:
        out["frequency_penalty"] = eff_freq
    if pe:
        out["presence_penalty"] = eff_pres
    if tpe:
        out["top_p"] = eff_top_p
    if mte and mt is not None and mt > 0:
        out["max_tokens"] = int(mt)
    return out


def format_llm_params_log_line(agent_name: str, prompt: "Prompt", kwargs: Dict[str, Any]) -> str:
    """Human-readable log line: only lists sampling args actually passed to the API."""
    temp_m = "custom" if getattr(prompt, "temperature_enabled", False) else "default"
    mt = kwargs.get("max_tokens")
    mt_str = str(mt) if mt is not None else "auto"
    parts = [
        f"[{agent_name}] LLM params: model={prompt.model}",
        f"temp={kwargs.get('temperature', 0.7):.1f} ({temp_m})",
        f"max_tokens={mt_str}",
    ]
    if "frequency_penalty" in kwargs:
        parts.append(f"freq={kwargs['frequency_penalty']} (custom)")
    if "presence_penalty" in kwargs:
        parts.append(f"pres={kwargs['presence_penalty']} (custom)")
    if "top_p" in kwargs:
        parts.append(f"top_p={kwargs['top_p']} (custom)")
    return ", ".join(parts)
