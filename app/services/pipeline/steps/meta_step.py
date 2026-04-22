from app.services.json_parser import clean_and_parse_json
from app.services.pipeline.errors import LLMError, ParseError
from app.services.pipeline.llm_client import call_agent
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.template_vars import setup_template_vars
from app.services.pipeline.assembly import pick_html_for_meta
from app.services.pipeline_constants import STEP_META_GEN


class MetaGenerationStep:
    name = STEP_META_GEN
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        structured_html = pick_html_for_meta(ctx)
        meta_context = f"Article HTML:\n{structured_html}"
        add_log(ctx.db, ctx.task, "Generating Meta Tags (JSON)...", step=STEP_META_GEN)
        meta_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx,
            "meta_generation",
            meta_context,
            response_format={"type": "json_object"},
            variables=ctx.template_vars,
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        if meta_json_str and not clean_and_parse_json(meta_json_str):
            raise ParseError("meta_generation returned unparseable JSON")
        raw_preview = (meta_json_str or "")[:500]
        add_log(
            ctx.db,
            ctx.task,
            f"meta_generation raw (first 500): {raw_preview}",
            level="debug",
            step=STEP_META_GEN,
        )
        add_log(ctx.db, ctx.task, "Meta Tags Generation completed", step=STEP_META_GEN)
        return StepResult(
            status="completed",
            result=meta_json_str,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


register_step(MetaGenerationStep())
