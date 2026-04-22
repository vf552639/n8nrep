"""Unit tests for prompt LLM sampling kwargs (task21 param flags)."""

from types import SimpleNamespace

from app.services.prompt_llm_kwargs import (
    format_llm_params_log_line,
    llm_sampling_kwargs_from_prompt,
)


def _prompt(**kw):
    base = dict(
        model="openai/gpt-4o",
        max_tokens=None,
        max_tokens_enabled=False,
        temperature=0.7,
        temperature_enabled=False,
        frequency_penalty=0.0,
        frequency_penalty_enabled=False,
        presence_penalty=0.0,
        presence_penalty_enabled=False,
        top_p=1.0,
        top_p_enabled=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_disabled_uses_defaults_no_max_tokens():
    p = _prompt(max_tokens=8000, max_tokens_enabled=False, temperature=0.3, temperature_enabled=False)
    k = llm_sampling_kwargs_from_prompt(p)
    assert "max_tokens" not in k
    assert k["temperature"] == 0.7
    assert "frequency_penalty" not in k
    assert "presence_penalty" not in k
    assert "top_p" not in k


def test_disabled_params_not_in_kwargs():
    p = _prompt()
    k = llm_sampling_kwargs_from_prompt(p)
    assert "top_p" not in k
    assert "frequency_penalty" not in k
    assert "presence_penalty" not in k
    assert "temperature" in k


def test_enabled_passes_custom_values():
    p = _prompt(
        max_tokens=4000,
        max_tokens_enabled=True,
        temperature=0.3,
        temperature_enabled=True,
        frequency_penalty=0.5,
        frequency_penalty_enabled=True,
        presence_penalty=-0.2,
        presence_penalty_enabled=True,
        top_p=0.9,
        top_p_enabled=True,
    )
    k = llm_sampling_kwargs_from_prompt(p)
    assert k["max_tokens"] == 4000
    assert k["temperature"] == 0.3
    assert k["frequency_penalty"] == 0.5
    assert k["presence_penalty"] == -0.2
    assert k["top_p"] == 0.9


def test_enabled_params_present_in_kwargs():
    p = _prompt(
        top_p=0.9,
        top_p_enabled=True,
        frequency_penalty=0.5,
        frequency_penalty_enabled=True,
    )
    k = llm_sampling_kwargs_from_prompt(p)
    assert k["top_p"] == 0.9
    assert k["frequency_penalty"] == 0.5
    assert "presence_penalty" not in k


def test_test_overrides_ignore_db_when_passed():
    p = _prompt(temperature=0.9, temperature_enabled=False)
    k = llm_sampling_kwargs_from_prompt(p, temperature_enabled=True, temperature=0.1)
    assert k["temperature"] == 0.1


def test_format_log_contains_custom_marker():
    p = _prompt(temperature_enabled=True)
    kwargs = {"temperature": 0.3}
    line = format_llm_params_log_line("primary_generation", p, kwargs)
    assert "primary_generation" in line
    assert "temp=0.3" in line
    assert "custom" in line
    assert "freq=" not in line
    assert "top_p=" not in line


def test_format_log_includes_optional_sampling_when_in_kwargs():
    p = _prompt(top_p_enabled=True, frequency_penalty_enabled=True)
    kwargs = {
        "temperature": 0.5,
        "max_tokens": 16000,
        "top_p": 0.9,
        "frequency_penalty": 0.2,
    }
    line = format_llm_params_log_line("meta_generation", p, kwargs)
    assert "meta_generation" in line
    assert "max_tokens=16000" in line
    assert "top_p=0.9 (custom)" in line
    assert "freq=0.2 (custom)" in line
    assert "pres=" not in line
