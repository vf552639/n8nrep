import re

from app.services.pipeline.errors import LLMError
from app.services.pipeline.llm_client import call_agent_with_exclude_validation
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.vars import setup_template_vars
from app.services.pipeline_constants import (
    STEP_FINAL_EDIT,
    STEP_IMPROVER,
    STEP_PRIMARY_GEN,
    STEP_PRIMARY_GEN_ABOUT,
    STEP_PRIMARY_GEN_LEGAL,
)
from app.services.word_counter import count_content_words


class FinalEditingStep:
    name = STEP_FINAL_EDIT
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=1)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        if ctx.use_serp:
            improved_html = ctx.task.step_results.get(STEP_IMPROVER, {}).get("result", "") or ""
            if not improved_html.strip():
                improved_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "") or ""
        else:
            improved_html = (
                ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
                or ctx.task.step_results.get(STEP_PRIMARY_GEN_ABOUT, {}).get("result", "")
                or ctx.task.step_results.get(STEP_PRIMARY_GEN_LEGAL, {}).get("result", "")
                or ""
            )

        ctx.template_vars["result_improver"] = improved_html or ""
        avg_words = ctx.template_vars.get("avg_word_count", "0")
        input_word_count = count_content_words(improved_html)
        input_char_count = len(improved_html)
        editing_context = ""
        add_log(ctx.db, ctx.task, "Starting Final Editing...", step=STEP_FINAL_EDIT)
        final_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = (
            call_agent_with_exclude_validation(
                ctx, "final_editing", editing_context, step_constant=STEP_FINAL_EDIT
            )
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        final_html = re.sub(r"\[.*?SCHEMA.*?\]", "", final_html, flags=re.IGNORECASE | re.DOTALL)
        final_html = re.sub(
            r"<script[^>]*application/ld\+json[^>]*>.*?</script>", "", final_html, flags=re.IGNORECASE | re.DOTALL
        )
        final_html = re.sub(r"\n{3,}", "\n\n", final_html)

        exclude_str = ctx.template_vars.get("exclude_words", "")
        if exclude_str.strip():
            from app.services.exclude_words_validator import ExcludeWordsValidator

            validator = ExcludeWordsValidator(exclude_str)
            final_report = validator.validate(final_html)
            if not final_report["passed"]:
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Force-removing remaining exclude words after final editing: {final_report['found_words']}",
                    level="warn",
                    step=STEP_FINAL_EDIT,
                )
                final_html, _ = validator.remove_violations(final_html)

        output_word_count = count_content_words(final_html)
        output_char_count = len(final_html)
        add_log(
            ctx.db,
            ctx.task,
            f"Final Editing completed | input: {input_word_count} words / {input_char_count} chars | "
            f"output: {output_word_count} words / {output_char_count} chars | "
            f"target avg: {avg_words} words",
            step=STEP_FINAL_EDIT,
        )
        return StepResult(
            status="completed",
            result=final_html,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
            extra={
                "exclude_words_violations": violations,
                "input_word_count": input_word_count,
                "output_word_count": output_word_count,
            },
        )


register_step(FinalEditingStep())
