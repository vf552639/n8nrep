import datetime
import time
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import settings
from app.models.prompt import Prompt
from app.services.exclude_words_validator import ExcludeWordsValidator
from app.services.llm import generate_text, timeout_for_model
from app.services.pipeline.errors import LLMError
from app.services.pipeline.persistence import add_log
from app.services.pipeline.vars import apply_template_vars
from app.services.pipeline_constants import CRITICAL_VARS, CRITICAL_VARS_ALLOW_EMPTY
from app.services.prompt_llm_kwargs import format_llm_params_log_line, llm_sampling_kwargs_from_prompt

if TYPE_CHECKING:
    from app.services.pipeline.context import PipelineContext


def get_prompt_obj(db: Session, agent_name: str) -> Prompt:
    prompt_obj = db.query(Prompt).filter(Prompt.agent_name == agent_name, Prompt.is_active.is_(True)).first()
    if not prompt_obj and agent_name == "content_fact_checking":
        prompt_obj = (
            db.query(Prompt).filter(Prompt.agent_name == "fact_checking", Prompt.is_active.is_(True)).first()
        )
    if not prompt_obj:
        raise LLMError(f"No active prompt found for agent: {agent_name}")
    return prompt_obj


def call_agent(
    ctx: "PipelineContext", agent_name: str, context: str, response_format=None, variables: dict = None
) -> tuple[str, float, str, dict, dict]:
    prompt = get_prompt_obj(ctx.db, agent_name)

    if getattr(prompt, "skip_in_pipeline", False):
        print(f"Agent {agent_name} skipped (toggle off)")
        return "", 0.0, prompt.model, {}, {}

    system_text = prompt.system_prompt
    user_template = prompt.user_prompt or ""

    resolved_prompts = {}
    variables_snapshot = {}

    if variables:
        system_text, sys_report = apply_template_vars(system_text, variables)
        user_template, user_report = apply_template_vars(user_template, variables)

        all_resolved = list(set(sys_report["resolved"] + user_report["resolved"]))
        all_unresolved = list(set(sys_report["unresolved"] + user_report["unresolved"]))
        all_empty = list(set(sys_report["empty"] + user_report["empty"]))

        log_msg = f"[VARS] agent={agent_name}"
        log_msg += f" | resolved: {', '.join(all_resolved) if all_resolved else '(none)'}"
        log_msg += f" | empty: {', '.join(all_empty) if all_empty else '(none)'}"
        log_msg += f" | unresolved: {', '.join(all_unresolved) if all_unresolved else '(none)'}"

        level = "info"
        if all_unresolved:
            level = "warn"

        add_log(ctx.db, ctx.task, log_msg, level=level, step=agent_name)

        critical = CRITICAL_VARS.get(agent_name, [])
        allow_empty_critical = CRITICAL_VARS_ALLOW_EMPTY.get(agent_name, frozenset())
        missing_critical = []
        for cv in critical:
            if cv in all_unresolved or (cv in all_empty and cv not in allow_empty_critical):
                missing_critical.append(cv)

        if missing_critical:
            err_msg = f"CRITICAL VARIABLES MISSING OR EMPTY for {agent_name}: {', '.join(missing_critical)}"
            add_log(ctx.db, ctx.task, err_msg, level="error", step=agent_name)
            if getattr(settings, "STRICT_VARIABLE_CHECK", False):
                raise ValueError(err_msg)

        for k, v in variables.items():
            val_str = str(v)
            variables_snapshot[k] = val_str[:200] + "..." if len(val_str) > 200 else val_str

        exclude_str = variables.get("exclude_words", "")
        if exclude_str.strip():
            words_list = [w.strip() for w in exclude_str.split(",") if w.strip()]
            if words_list:
                exclude_instruction = (
                    "\n\n[BANNED WORDS — CRITICAL RULE]\n"
                    "You MUST NOT use ANY of the following words in your output, "
                    "in any form (including variations, plurals, different cases). "
                    "These words are strictly forbidden and their presence will cause "
                    "the output to be rejected:\n"
                    f"{', '.join(words_list)}\n"
                    "Use synonyms or rephrase completely. "
                    "This rule has the HIGHEST priority and overrides all other instructions."
                )
                system_text += exclude_instruction

        if agent_name == "final_editing":
            schema_instruction = (
                "\n\n[SCHEMA/JSON-LD PROHIBITION — CRITICAL RULE]\n"
                "You MUST NOT include any Schema.org markup, JSON-LD scripts, "
                "or placeholder blocks like [SCHEMA: ...], [🛠️ SCHEMA: ...], "
                '<script type="application/ld+json">, or any references to structured data markup '
                "in your output. Do NOT suggest, mention, or output any Schema.org related content. "
                "Your output must be pure article HTML only (p, h2, h3, ul, ol, strong, em, a tags). "
                "This rule has the HIGHEST priority."
            )
            system_text += schema_instruction

    if user_template:
        ctx_text = (context or "").strip()
        if ctx_text:
            user_msg = f"{user_template}\n\n[CONTEXT]\n{context}"
        else:
            user_msg = user_template
    else:
        user_msg = context or ""

    step_results = ctx.task.step_results or {}
    rerun_feedback = step_results.get("_rerun_feedback", {})
    if rerun_feedback.get("step") == agent_name and rerun_feedback.get("feedback"):
        user_msg += f"\n\n[HUMAN FEEDBACK ON PREVIOUS VERSION]\n{rerun_feedback['feedback']}"
        add_log(
            ctx.db,
            ctx.task,
            f"Injected human feedback into prompt for {agent_name}",
            level="info",
            step=agent_name,
        )
        new_results = dict(step_results)
        del new_results["_rerun_feedback"]
        ctx.task.step_results = new_results
        ctx.db.commit()

    resolved_prompts["system_prompt"] = system_text[:6000]
    resolved_prompts["user_prompt"] = user_msg[:6000]

    total_chars = len(system_text) + len(user_msg)
    print(
        f"[call_agent] {agent_name} | model={prompt.model} | "
        f"system={len(system_text)} chars | user={len(user_msg)} chars | "
        f"total={total_chars} chars (~{total_chars // 4} tokens est.)"
    )
    est_tokens = total_chars // 4
    if est_tokens > 50000:
        add_log(
            ctx.db,
            ctx.task,
            f"Large context for {agent_name}: ~{est_tokens} tokens estimated",
            level="warn",
            step=agent_name,
        )

    sampling = llm_sampling_kwargs_from_prompt(prompt)
    kwargs = {
        "system_prompt": system_text,
        "user_prompt": user_msg,
        "model": prompt.model,
        **sampling,
    }
    if response_format:
        kwargs["response_format"] = response_format

    def _touch_heartbeat():
        ctx.task.last_heartbeat = datetime.datetime.utcnow()
        ctx.db.commit()

    requested_model = prompt.model

    def _on_llm_progress(event: str, payload: dict):
        if event == "retry_wait":
            add_log(
                ctx.db,
                ctx.task,
                (
                    f"[{agent_name}] Retry {payload.get('attempt')}/{payload.get('max_retries')}: "
                    f"{payload.get('reason')}. Sleeping {payload.get('sleep_seconds')}s"
                ),
                level="warn",
                step=agent_name,
            )
            _touch_heartbeat()
        elif event == "response_received":
            usage = payload.get("usage") or {}
            p = usage.get("prompt_tokens", 0)
            c = usage.get("completion_tokens", 0)
            cached = usage.get("cached_tokens", 0)
            reasoning = usage.get("reasoning_tokens", 0)

            tokens_msg = f"{p}+{c} tokens"
            if cached > 0:
                tokens_msg += f" | ⚡ {cached} cached"
            if reasoning > 0:
                tokens_msg += f" | 🧠 {reasoning} reasoning"

            actual_m = payload.get("model")
            fallback_note = ""
            if actual_m and requested_model and str(actual_m) != str(requested_model):
                fallback_note = f" | ⚠ fallback to {actual_m}"

            add_log(
                ctx.db,
                ctx.task,
                (
                    f"[{agent_name}] LLM response received "
                    f"({tokens_msg}, ${float(payload.get('cost') or 0.0):.5f}){fallback_note}"
                ),
                level="info",
                step=agent_name,
            )
            _touch_heartbeat()

    add_log(
        ctx.db,
        ctx.task,
        format_llm_params_log_line(agent_name, prompt, kwargs),
        level="info",
        step=agent_name,
    )
    _touch_heartbeat()
    kwargs["timeout"] = int(timeout_for_model(prompt.model))
    kwargs["progress_callback"] = _on_llm_progress

    try:
        res, cost, model, _ = generate_text(**kwargs)
    except Exception as e:
        raise LLMError(f"{agent_name}: LLM call failed: {e}") from e
    return res, cost, model, resolved_prompts, variables_snapshot


def call_agent_with_exclude_validation(
    ctx: "PipelineContext",
    agent_name: str,
    context: str,
    step_constant: str,
    max_retries: int | None = None,
):
    if max_retries is None:
        max_retries = getattr(settings, "SELF_CHECK_MAX_RETRIES", 1)
    retry_budget = float(getattr(settings, "SELF_CHECK_MAX_COST_PER_STEP", 0.10) or 0.0)
    retry_spent = 0.0

    result_text, total_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, agent_name, context, variables=ctx.template_vars
    )

    exclude_str = ctx.template_vars.get("exclude_words", "")
    if not exclude_str.strip():
        return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, None

    validator = ExcludeWordsValidator(exclude_str)
    report = validator.validate(result_text)

    if report["passed"]:
        return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, None

    add_log(
        ctx.db,
        ctx.task,
        f"EXCLUDE_WORDS violation: found {report['found_words']}",
        level="warn",
        step=step_constant,
    )

    retry_count = 0
    while retry_count < max_retries and not report["passed"]:
        if ctx.step_deadline is not None and time.monotonic() > ctx.step_deadline:
            add_log(
                ctx.db,
                ctx.task,
                "Step wall-clock budget exhausted; skipping further exclude-word retries.",
                level="warn",
                step=step_constant,
            )
            break
        if retry_budget > 0 and retry_spent >= retry_budget:
            add_log(
                ctx.db,
                ctx.task,
                f"Budget limit reached for exclude-word retries (${retry_spent:.4f}). Using best result.",
                level="warn",
                step=step_constant,
            )
            break
        retry_count += 1
        add_log(
            ctx.db,
            ctx.task,
            f"Retrying agent {agent_name} due to exclude words violation (Attempt {retry_count}).",
            level="info",
            step=step_constant,
        )

        retry_context = context + (
            f"\n\nCRITICAL: Your previous output contained forbidden words: {report['found_words']}. "
            f"You MUST NOT use these words. Rewrite the text avoiding them completely."
        )

        retry_text, retry_cost, r_model, r_prompts, r_vars = call_agent(
            ctx, agent_name, retry_context, variables=ctx.template_vars
        )
        retry_spent += retry_cost
        total_cost += retry_cost
        result_text = retry_text
        actual_model = r_model
        resolved_prompts = r_prompts
        variables_snapshot = r_vars

        report = validator.validate(result_text)

    violations_dict = None
    if not report["passed"]:
        add_log(
            ctx.db,
            ctx.task,
            f"EXCLUDE_WORDS violation persists after retries: found {report['found_words']}",
            level="error",
            step=step_constant,
        )
        violations_dict = report["found_words"]

    return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, violations_dict
