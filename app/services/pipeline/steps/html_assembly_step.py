from app.config import settings
from app.services.html_inserter import programmatic_html_insert
from app.services.pipeline.errors import LLMError
from app.services.pipeline.llm_client import call_agent
from app.services.pipeline.persistence import _completed_step_body, add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.vars import setup_template_vars
from app.services.pipeline_constants import (
    STEP_CONTENT_FACT_CHECK,
    STEP_FINAL_EDIT,
    STEP_HTML_STRUCT,
    STEP_IMPROVER,
    STEP_PRIMARY_GEN,
    STEP_PRIMARY_GEN_ABOUT,
    STEP_PRIMARY_GEN_LEGAL,
)
from app.services.word_counter import count_content_words


class HtmlStructureStep:
    name = STEP_HTML_STRUCT
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        final_html = _completed_step_body(ctx.task, STEP_FINAL_EDIT)
        if not final_html:
            for key in (STEP_IMPROVER, STEP_PRIMARY_GEN, STEP_PRIMARY_GEN_ABOUT, STEP_PRIMARY_GEN_LEGAL):
                final_html = _completed_step_body(ctx.task, key)
                if final_html:
                    break

        template_ref = ""
        if ctx.template_vars.get("site_template_html"):
            template_ref = (
                f"\n\n[SITE TEMPLATE REFERENCE]\n"
                f"Template Name: {ctx.template_vars.get('site_template_name', 'N/A')}\n"
                f"The generated content will be inserted into this template via {{{{content}}}} placeholder.\n"
                f"Adapt your HTML structure to be compatible with this template:\n"
                f"{ctx.template_vars['site_template_html']}"
            )

        html_struct_context = (
            f"Article HTML:\n{final_html}\n\n"
            f"Keyword: {ctx.task.main_keyword}\n"
            f"Language: {ctx.task.language}"
            f"{template_ref}"
        )
        add_log(ctx.db, ctx.task, "Starting HTML Structure formatting...", step=STEP_HTML_STRUCT)
        structured_html, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "html_structure", html_struct_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost

        input_wc = count_content_words(final_html)
        output_wc = count_content_words(structured_html)
        loss_pct = ((input_wc - output_wc) / input_wc * 100.0) if input_wc > 0 else 0.0

        max_rec = getattr(settings, "SELF_CHECK_MAX_RETRIES", 1)
        retry_budget = float(getattr(settings, "SELF_CHECK_MAX_COST_PER_STEP", 0.10) or 0.0)

        if input_wc > 0 and loss_pct > 7 and max_rec >= 1 and retry_budget > 0:
            add_log(
                ctx.db,
                ctx.task,
                f"Content loss {loss_pct:.1f}% detected, attempting recovery (single retry)...",
                level="warn",
                step=STEP_HTML_STRUCT,
            )
            prev_loss = loss_pct
            recovery_context = (
                f"PREVIOUS ATTEMPT FAILED: You lost {prev_loss:.1f}% of content words.\n"
                f"Input had {input_wc} words but your output only had {output_wc} words.\n\n"
                f"YOU MUST OUTPUT ALL {input_wc} WORDS from the article below.\n"
                f"Do NOT summarize or shorten. Insert the COMPLETE article into the template.\n\n"
                f"{html_struct_context}"
            )
            retry_html, retry_cost, retry_model, retry_prompts, retry_vars = call_agent(
                ctx, "html_structure", recovery_context, variables=ctx.template_vars
            )
            ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + retry_cost
            if retry_cost > retry_budget:
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Recovery retry cost ${retry_cost:.4f} exceeded per-step retry budget ${retry_budget:.4f}.",
                    level="warn",
                    step=STEP_HTML_STRUCT,
                )
            retry_wc = count_content_words(retry_html)
            retry_loss = ((input_wc - retry_wc) / input_wc * 100.0) if input_wc > 0 else 0.0
            if retry_loss < prev_loss:
                structured_html = retry_html
                output_wc = retry_wc
                loss_pct = retry_loss
                step_cost += retry_cost
                actual_model = retry_model
                resolved_prompts = retry_prompts
                variables_snapshot = retry_vars
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Recovery improved: {retry_loss:.1f}% loss (was {prev_loss:.1f}%)",
                    step=STEP_HTML_STRUCT,
                )

        if input_wc > 0 and loss_pct > 20:
            add_log(
                ctx.db,
                ctx.task,
                f"Content loss still {loss_pct:.1f}% after recovery. Using programmatic insert.",
                level="warn",
                step=STEP_HTML_STRUCT,
            )
            template_raw = ctx.template_vars.get("site_template_html", "") or ""
            structured_html = programmatic_html_insert(template_raw, final_html)
            output_wc = count_content_words(structured_html)
            loss_pct = ((input_wc - output_wc) / input_wc * 100.0) if input_wc > 0 else 0.0
            add_log(
                ctx.db,
                ctx.task,
                f"Programmatic HTML insert: {output_wc} words, loss now {loss_pct:.1f}%",
                level="info",
                step=STEP_HTML_STRUCT,
            )

        extra = {
            "input_word_count": input_wc,
            "output_word_count": output_wc,
        }
        if input_wc > 0 and loss_pct > 7:
            add_log(
                ctx.db,
                ctx.task,
                f"⚠️ WORD COUNT DROP: html_structure lost {loss_pct:.1f}% of content words! "
                f"Input: {input_wc} words → Output: {output_wc} words. "
                f"Maximum allowed loss: 7%",
                level="warn",
                step=STEP_HTML_STRUCT,
            )
            extra["word_count_warning"] = True
            extra["word_loss_percentage"] = round(loss_pct, 1)

        add_log(
            ctx.db, ctx.task, f"HTML Structure completed ({len(structured_html)} chars)", step=STEP_HTML_STRUCT
        )
        return StepResult(
            status="completed",
            result=structured_html,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
            extra=extra,
        )


class ContentFactCheckStep:
    name = STEP_CONTENT_FACT_CHECK
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=1)

    def run(self, ctx) -> StepResult:
        if not settings.FACT_CHECK_ENABLED:
            return StepResult(
                status="completed",
                result='{"verification_status": "skipped", "issues": [], "summary": "Fact-check disabled in settings."}',
            )

        setup_template_vars(ctx)
        final_html = ctx.task.step_results.get(STEP_FINAL_EDIT, {}).get("result", "")
        ctx.template_vars["final_article"] = final_html
        ctx.template_vars["scraped_competitors_text"] = (
            ctx.task.competitors_text[:15000] if ctx.task.competitors_text else ""
        )
        fact_check_context = (
            f"Final Article HTML:\n{final_html}\n\n"
            f"Keyword: {ctx.task.main_keyword}\n"
            f"Language: {ctx.task.language}\n"
            f"Country: {ctx.task.country}"
        )

        add_log(ctx.db, ctx.task, "Starting Fact-Checking...", step=STEP_CONTENT_FACT_CHECK)
        try:
            fact_check_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
                ctx,
                "content_fact_checking",
                fact_check_context,
                response_format={"type": "json_object"},
                variables=ctx.template_vars,
            )
            ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
            add_log(ctx.db, ctx.task, "Fact-Checking completed", step=STEP_CONTENT_FACT_CHECK)
            return StepResult(
                status="completed",
                result=fact_check_json_str,
                model=actual_model,
                cost=step_cost,
                variables_snapshot=variables_snapshot,
                resolved_prompts=resolved_prompts,
            )
        except Exception as e:
            add_log(
                ctx.db,
                ctx.task,
                f"Fact-checking agent failed or not found: {e!s}",
                level="warn",
                step=STEP_CONTENT_FACT_CHECK,
            )
            return StepResult(
                status="completed",
                result='{"verification_status": "warn", "issues": [], "summary": "Failed to run content_fact_checking agent."}',
            )


register_step(HtmlStructureStep())
register_step(ContentFactCheckStep())
