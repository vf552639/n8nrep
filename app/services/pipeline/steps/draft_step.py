import json

from app.services.pipeline.errors import LLMError
from app.services.pipeline.llm_client import call_agent
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.template_vars import setup_template_vars
from app.services.pipeline_constants import (
    STEP_COMP_COMPARISON,
    STEP_IMPROVER,
    STEP_INTERLINK,
    STEP_PRIMARY_GEN,
    STEP_PRIMARY_GEN_ABOUT,
    STEP_READER_OPINION,
)
from app.services.word_counter import count_content_words


class PrimaryGenStep:
    name = STEP_PRIMARY_GEN
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        outline_json = ctx.task.outline.get("final_outline", {})
        gen_context = (
            f"Keyword: {ctx.task.main_keyword}\n"
            f"Language: {ctx.task.language}\n"
            f"{ctx.author_block}\n"
            f"Outline: {json.dumps(outline_json, ensure_ascii=False)}"
        )
        add_log(ctx.db, ctx.task, "Starting Primary Generation...", step=STEP_PRIMARY_GEN)
        draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "primary_generation", gen_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(
            ctx.db, ctx.task, f"Primary Generation completed ({len(draft_html)} chars)", step=STEP_PRIMARY_GEN
        )
        out_wc = count_content_words(draft_html)
        return StepResult(
            status="completed",
            result=draft_html,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
            extra={"output_word_count": out_wc},
        )


class PrimaryGenAboutStep:
    name = STEP_PRIMARY_GEN_ABOUT
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        gen_context = ""
        add_log(ctx.db, ctx.task, "Starting Primary Generation (About Page)...", step=STEP_PRIMARY_GEN_ABOUT)
        draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "primary_generation_about", gen_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(
            ctx.db,
            ctx.task,
            f"Primary Generation (About) completed ({len(draft_html)} chars)",
            step=STEP_PRIMARY_GEN_ABOUT,
        )
        out_wc = count_content_words(draft_html)
        return StepResult(
            status="completed",
            result=draft_html,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
            extra={"output_word_count": out_wc},
        )


class CompetitorComparisonStep:
    name = STEP_COMP_COMPARISON
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
        comparison_context = f"Our article:\n{draft_html}\n\nCompetitors:\n{ctx.task.competitors_text[:15000]}"
        add_log(ctx.db, ctx.task, "Starting Competitor Comparison...", step=STEP_COMP_COMPARISON)
        comparison_review, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "competitor_comparison", comparison_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(ctx.db, ctx.task, "Competitor Comparison completed", step=STEP_COMP_COMPARISON)
        return StepResult(
            status="completed",
            result=comparison_review,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class ReaderOpinionStep:
    name = STEP_READER_OPINION
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
        reader_context = f"Article:\n{draft_html}"
        add_log(ctx.db, ctx.task, "Starting Reader Opinion analysis...", step=STEP_READER_OPINION)
        reader_feedback, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "reader_opinion", reader_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(ctx.db, ctx.task, "Reader Opinion completed", step=STEP_READER_OPINION)
        return StepResult(
            status="completed",
            result=reader_feedback,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class InterlinkStep:
    name = STEP_INTERLINK
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
        interlink_context = (
            f"Article:\n{draft_html}\n\n"
            f"Keyword: {ctx.task.main_keyword}\n"
            f"Language: {ctx.task.language}\n"
            f"Site: {ctx.site_name}"
        )
        add_log(ctx.db, ctx.task, "Starting Interlinking & Citations...", step=STEP_INTERLINK)
        interlink_suggestions, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "interlinking_citations", interlink_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(ctx.db, ctx.task, "Interlinking & Citations completed", step=STEP_INTERLINK)
        return StepResult(
            status="completed",
            result=interlink_suggestions,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class ImproverStep:
    name = STEP_IMPROVER
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
        comparison_review = ctx.task.step_results.get(STEP_COMP_COMPARISON, {}).get("result", "")
        reader_feedback = ctx.task.step_results.get(STEP_READER_OPINION, {}).get("result", "")
        interlink_suggestions = ctx.task.step_results.get(STEP_INTERLINK, {}).get("result", "")
        improver_context = (
            f"Draft:\n{draft_html}\n\n"
            f"Competitor Comparison Review:\n{comparison_review}\n\n"
            f"Reader Feedback:\n{reader_feedback}\n\n"
            f"Interlinking & Citations Suggestions:\n{interlink_suggestions}"
        )
        add_log(ctx.db, ctx.task, "Starting Improver (draft enhancement)...", step=STEP_IMPROVER)
        improved_html, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "improver", improver_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(ctx.db, ctx.task, f"Improver completed ({len(improved_html)} chars)", step=STEP_IMPROVER)
        in_wc = count_content_words(draft_html)
        out_wc = count_content_words(improved_html)
        return StepResult(
            status="completed",
            result=improved_html,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
            extra={
                "input_word_count": in_wc,
                "output_word_count": out_wc,
            },
        )


register_step(PrimaryGenStep())
register_step(PrimaryGenAboutStep())
register_step(CompetitorComparisonStep())
register_step(ReaderOpinionStep())
register_step(InterlinkStep())
register_step(ImproverStep())
