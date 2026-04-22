from app.services.json_parser import clean_and_parse_json
from app.services.pipeline.errors import LLMError
from app.services.pipeline.llm_client import call_agent
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.vars import setup_template_vars, setup_vars
from app.services.pipeline_constants import (
    STEP_AI_ANALYSIS,
    STEP_CHUNK_ANALYSIS,
    STEP_COMP_STRUCTURE,
    STEP_FINAL_ANALYSIS,
    STEP_STRUCTURE_FACT_CHECK,
)


class AiStructureStep:
    name = STEP_AI_ANALYSIS
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        ctx.db.refresh(ctx.task)
        setup_vars(ctx)
        add_log(ctx.db, ctx.task, "Starting AI Structure Analysis...", step=STEP_AI_ANALYSIS)
        ai_structure, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx,
            "ai_structure_analysis",
            ctx.base_context,
            response_format={"type": "json_object"},
            variables=ctx.analysis_vars,
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        ctx.analysis_vars["result_ai_structure_analysis"] = ai_structure
        ctx.outline_data["ai_structure"] = ai_structure

        add_log(
            ctx.db,
            ctx.task,
            f"ai_structure raw (first 500): {ai_structure[:500]}",
            level="debug",
            step=STEP_AI_ANALYSIS,
        )

        ai_struct_data = clean_and_parse_json(
            ai_structure,
            unwrap_keys={"intent", "Taxonomy", "Attention", "structura"},
        )
        if ai_struct_data:
            ctx.analysis_vars["intent"] = ai_struct_data.get("intent", "")
            ctx.analysis_vars["Taxonomy"] = ai_struct_data.get("Taxonomy", "")
            ctx.analysis_vars["Attention"] = ai_struct_data.get("Attention", "")
            ctx.analysis_vars["structura"] = ai_struct_data.get("structura", "")
            ctx.outline_data["ai_structure_parsed"] = ai_struct_data
            if not ai_struct_data.get("intent"):
                add_log(
                    ctx.db,
                    ctx.task,
                    "Warning: 'intent' is empty after parsing ai_structure",
                    level="warn",
                    step=STEP_AI_ANALYSIS,
                )
        else:
            add_log(
                ctx.db,
                ctx.task,
                "Warning: Failed to parse ai_structure_analysis JSON",
                level="warn",
                step=STEP_AI_ANALYSIS,
            )

        ctx.task.outline = ctx.outline_data
        ctx.db.commit()
        final_status = "completed_with_warnings" if not ai_struct_data or not ai_struct_data.get("intent") else "completed"
        add_log(
            ctx.db,
            ctx.task,
            f"AI Structure Analysis completed ({len(ai_structure)} chars)",
            step=STEP_AI_ANALYSIS,
        )
        return StepResult(
            status=final_status,
            result=ai_structure,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class ChunkAnalysisStep:
    name = STEP_CHUNK_ANALYSIS
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        ctx.db.refresh(ctx.task)
        setup_vars(ctx)
        add_log(ctx.db, ctx.task, "Starting Chunk Cluster Analysis...", step=STEP_CHUNK_ANALYSIS)
        ai_structure = ctx.outline_data.get("ai_structure", "")
        chunk_context = f"{ctx.base_context}\n\nAI Structure Analysis:\n{ai_structure}"
        chunk_analysis, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "chunk_cluster_analysis", chunk_context, variables=ctx.analysis_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        ctx.analysis_vars["result_chunk_cluster_analysis"] = chunk_analysis
        ctx.outline_data["chunk_analysis"] = chunk_analysis
        ctx.task.outline = ctx.outline_data
        ctx.db.commit()
        add_log(
            ctx.db,
            ctx.task,
            f"Chunk Cluster Analysis completed ({len(chunk_analysis)} chars)",
            step=STEP_CHUNK_ANALYSIS,
        )
        return StepResult(
            status="completed",
            result=chunk_analysis,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class CompetitorStructureStep:
    name = STEP_COMP_STRUCTURE
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        ctx.db.refresh(ctx.task)
        setup_vars(ctx)
        add_log(ctx.db, ctx.task, "Starting Competitor Structure Analysis...", step=STEP_COMP_STRUCTURE)
        chunk_analysis = ctx.outline_data.get("chunk_analysis", "")
        competitor_context = (
            f"{ctx.base_context}\n\n"
            f"Competitors Text:\n{ctx.task.competitors_text[:20000]}\n\n"
            f"Chunk Analysis:\n{chunk_analysis}"
        )
        competitor_structure, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "competitor_structure_analysis", competitor_context, variables=ctx.analysis_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        ctx.analysis_vars["result_competitor_structure_analysis"] = competitor_structure
        ctx.outline_data["competitor_structure"] = competitor_structure
        ctx.task.outline = ctx.outline_data
        ctx.db.commit()
        add_log(
            ctx.db,
            ctx.task,
            f"Competitor Structure Analysis completed ({len(competitor_structure)} chars)",
            step=STEP_COMP_STRUCTURE,
        )
        return StepResult(
            status="completed",
            result=competitor_structure,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class FinalStructureStep:
    name = STEP_FINAL_ANALYSIS
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        ctx.db.refresh(ctx.task)
        setup_vars(ctx)
        add_log(ctx.db, ctx.task, "Starting Final Structure Analysis (JSON)...", step=STEP_FINAL_ANALYSIS)
        final_analysis_context = (
            f"{ctx.base_context}\n\n"
            f"AI Structure Analysis:\n{ctx.outline_data.get('ai_structure', '')}\n\n"
            f"Chunk Analysis:\n{ctx.outline_data.get('chunk_analysis', '')}\n\n"
            f"Competitor Structure Analysis:\n{ctx.outline_data.get('competitor_structure', '')}"
        )
        outline_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx,
            "final_structure_analysis",
            final_analysis_context,
            response_format={"type": "json_object"},
            variables=ctx.analysis_vars,
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        ctx.outline_data["final_outline"] = clean_and_parse_json(outline_json_str)
        ctx.outline_data["final_structure"] = outline_json_str
        ctx.task.outline = ctx.outline_data
        ctx.db.commit()
        add_log(ctx.db, ctx.task, "Final Structure Analysis completed", step=STEP_FINAL_ANALYSIS)
        return StepResult(
            status="completed",
            result=outline_json_str,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


class StructureFactCheckStep:
    name = STEP_STRUCTURE_FACT_CHECK
    policy = StepPolicy(retryable_errors=(LLMError,), max_retries=2)

    def run(self, ctx) -> StepResult:
        setup_template_vars(ctx)
        add_log(ctx.db, ctx.task, "Starting Structure Fact-Checking...", step=STEP_STRUCTURE_FACT_CHECK)
        fact_check_report, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "structure_fact_checking", "", variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
        add_log(
            ctx.db,
            ctx.task,
            f"Structure Fact-Checking completed ({len(fact_check_report)} chars)",
            step=STEP_STRUCTURE_FACT_CHECK,
        )
        return StepResult(
            status="completed",
            result=fact_check_report,
            model=actual_model,
            cost=step_cost,
            variables_snapshot=variables_snapshot,
            resolved_prompts=resolved_prompts,
        )


register_step(AiStructureStep())
register_step(ChunkAnalysisStep())
register_step(CompetitorStructureStep())
register_step(FinalStructureStep())
register_step(StructureFactCheckStep())
