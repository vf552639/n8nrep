from app.services.legal_reference import inject_legal_template_vars
from app.services.pipeline.errors import LLMError
from app.services.pipeline.llm_client import call_agent_with_exclude_validation
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.vars import setup_template_vars
from app.services.pipeline_constants import STEP_PRIMARY_GEN_LEGAL
from app.services.word_counter import count_content_words


class PrimaryGenLegalStep:
    name = STEP_PRIMARY_GEN_LEGAL
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=1)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        inject_legal_template_vars(ctx)
        gen_context = ""
        add_log(ctx.db, ctx.task, "Starting Primary Generation (Legal Page)...", step=STEP_PRIMARY_GEN_LEGAL)
        draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = (
            call_agent_with_exclude_validation(
                ctx,
                "primary_generation_legal",
                gen_context,
                step_constant=STEP_PRIMARY_GEN_LEGAL,
            )
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(
            ctx.db,
            ctx.task,
            f"Primary Generation (Legal) completed ({len(draft_html)} chars)",
            step=STEP_PRIMARY_GEN_LEGAL,
        )
        out_wc = count_content_words(draft_html)
        return StepResult(
            status="completed",
            result=draft_html,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
            extra={"exclude_words_violations": violations, "output_word_count": out_wc},
        )


register_step(PrimaryGenLegalStep())
