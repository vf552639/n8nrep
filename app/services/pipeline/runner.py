import json
import signal
import traceback

from sqlalchemy.orm import Session

from app.config import settings
from app.services.notifier import notify_task_failed, notify_task_success
from app.services.pipeline import steps as _steps_pkg  # noqa: F401
from app.services.pipeline.assembly import finalize_article
from app.services.pipeline.context import PipelineContext
from app.services.pipeline.errors import StepTimeoutError
from app.services.pipeline.persistence import add_log, mark_step_running, save_step_result
from app.services.pipeline.registry import STEP_REGISTRY
from app.services.pipeline.steps.base import PipelineStep, StepResult
from app.services.pipeline_constants import (
    STEP_FINAL_EDIT,
    STEP_HTML_STRUCT,
    STEP_IMAGE_GEN,
    STEP_META_GEN,
    STEP_PRIMARY_GEN,
    STEP_SERP,
)
from app.services.pipeline_presets import PIPELINE_PRESETS, pipeline_steps_use_serp

ALLOWED_EXTRA_FIELDS = frozenset(
    {
        "exclude_words_violations",
        "input_word_count",
        "output_word_count",
        "word_count_warning",
        "word_loss_percentage",
    }
)


def _auto_approve_images(ctx: PipelineContext) -> None:
    step_results = dict(ctx.task.step_results or {})
    image_gen_result = step_results.get(STEP_IMAGE_GEN, {}).get("result", "")
    if not image_gen_result:
        step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
        step_results["_images_approved"] = True
        ctx.task.step_results = step_results
        ctx.db.commit()
        add_log(
            ctx.db,
            ctx.task,
            "auto_mode: no image_generation payload — cleared image pause",
            step=STEP_IMAGE_GEN,
        )
        return
    try:
        data = json.loads(image_gen_result) if isinstance(image_gen_result, str) else image_gen_result
    except Exception:
        step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
        step_results["_images_approved"] = True
        ctx.task.step_results = step_results
        ctx.db.commit()
        add_log(
            ctx.db,
            ctx.task,
            "auto_mode: could not parse image_generation JSON — cleared image pause",
            level="warn",
            step=STEP_IMAGE_GEN,
        )
        return
    images = data.get("images", [])
    approved_n = 0
    for img in images:
        if img.get("status") == "completed" and img.get("hosted_url"):
            img["approved"] = True
            approved_n += 1
        else:
            img["approved"] = False
    step_data = dict(step_results.get(STEP_IMAGE_GEN, {}))
    step_data["result"] = json.dumps(data, ensure_ascii=False)
    step_results[STEP_IMAGE_GEN] = step_data
    step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
    step_results["_images_approved"] = True
    ctx.task.step_results = step_results
    ctx.db.commit()
    add_log(
        ctx.db,
        ctx.task,
        f"auto_mode: approved {approved_n} image(s) with completed status, continuing pipeline",
        step=STEP_IMAGE_GEN,
    )


def _call_with_timeout(step: PipelineStep, ctx: PipelineContext, timeout_sec: int) -> StepResult:
    old_handler = None
    alarm_enabled = False
    try:
        if hasattr(signal, "SIGALRM"):
            # SIGALRM works only in main thread.
            # In non-main threads timeout is silently skipped.
            def _handler(signum, frame):
                raise StepTimeoutError(f"Step {step.name} timed out after {timeout_sec}s")

            try:
                old_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, _handler)
                signal.alarm(timeout_sec)
                alarm_enabled = True
            except ValueError:
                alarm_enabled = False
        return step.run(ctx)
    finally:
        if alarm_enabled and hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)


def _run_phase(ctx: PipelineContext, step: PipelineStep) -> None:
    sr = ctx.task.step_results or {}
    existing_status = sr.get(step.name, {}).get("status")
    if existing_status in ("completed", "completed_with_warnings"):
        return

    mark_step_running(ctx.db, ctx.task, step.name)
    timeout_sec = int((step.policy.timeout_minutes or getattr(settings, "STEP_TIMEOUT_MINUTES", 15)) * 60)

    attempts = 0
    while True:
        try:
            result = _call_with_timeout(step, ctx, timeout_sec)
            unknown_extra = set(result.extra) - ALLOWED_EXTRA_FIELDS
            if unknown_extra:
                raise ValueError(f"Unknown extra fields from {step.name}: {sorted(unknown_extra)}")
            save_step_result(
                ctx.db,
                ctx.task,
                step.name,
                result=result.result,
                model=result.model,
                cost=result.cost,
                status=result.status,
                variables_snapshot=result.variables_snapshot,
                resolved_prompts=result.resolved_prompts,
                **result.extra,
            )
            return
        except StepTimeoutError as e:
            save_step_result(ctx.db, ctx.task, step.name, result=str(e), status="failed")
            add_log(ctx.db, ctx.task, f"❌ {step.name} timed out", level="error", step=step.name)
            raise
        except step.policy.skip_on as e:
            save_step_result(ctx.db, ctx.task, step.name, result=None, status="skipped")
            add_log(ctx.db, ctx.task, f"⚠️ {step.name} skipped: {e}", level="warn", step=step.name)
            return
        except step.policy.retryable_errors as e:
            attempts += 1
            if attempts > step.policy.max_retries:
                raise
            add_log(
                ctx.db,
                ctx.task,
                f"↩️ {step.name} retry {attempts}/{step.policy.max_retries}: {e}",
                level="warn",
                step=step.name,
            )


def _handle_pause_on_entry(ctx: PipelineContext) -> bool:
    """Returns True if pipeline should stop (still paused), False to continue."""
    step_results = ctx.task.step_results or {}
    pause_state = step_results.get("_pipeline_pause", {})
    if not (isinstance(pause_state, dict) and pause_state.get("active")):
        return False

    reason = pause_state.get("reason", "unknown")
    if reason == "image_review" and not step_results.get("_images_approved"):
        if not ctx.auto_mode:
            add_log(ctx.db, ctx.task, "⏸️ Pipeline paused: waiting for image review")
            return True
        _auto_approve_images(ctx)
    elif reason == "serp_review" and not step_results.get("_serp_urls_approved"):
        if not ctx.auto_mode:
            add_log(ctx.db, ctx.task, "⏸️ Pipeline paused: waiting for SERP URLs review")
            ctx.task.status = "paused"
            ctx.db.commit()
            return True
        updated = dict(step_results)
        updated["_serp_urls_approved"] = True
        updated["_pipeline_pause"] = {"active": False, "reason": "serp_review"}
        ctx.task.step_results = updated
        ctx.db.commit()
        add_log(ctx.db, ctx.task, "auto_mode: skipped SERP URL review pause")
    elif reason == "test_mode" and not step_results.get("test_mode_approved"):
        if not ctx.auto_mode:
            add_log(ctx.db, ctx.task, "⏸️ Pipeline paused: waiting for test mode approval")
            return True
        updated = dict(step_results)
        updated["test_mode_approved"] = True
        updated["waiting_for_approval"] = False
        updated["_pipeline_pause"] = {"active": False, "reason": "test_mode"}
        ctx.task.step_results = updated
        ctx.db.commit()
        add_log(ctx.db, ctx.task, "auto_mode: test mode approval applied, continuing")
    else:
        updated = dict(step_results)
        updated["_pipeline_pause"] = {"active": False, "reason": reason}
        ctx.task.step_results = updated
        ctx.db.commit()
    return False


def _handle_pause_after_step(ctx: PipelineContext, step_name: str) -> bool:
    if step_name == STEP_SERP:
        sr = dict(ctx.task.step_results or {})
        pause_st = sr.get("_pipeline_pause", {})
        if (
            isinstance(pause_st, dict)
            and pause_st.get("active")
            and pause_st.get("reason") == "serp_review"
            and not sr.get("_serp_urls_approved")
            and not ctx.auto_mode
        ):
            return True

    if step_name.startswith("primary_generation") and settings.TEST_MODE:
        step_results = ctx.task.step_results or {}
        if not step_results.get("test_mode_approved"):
            if ctx.auto_mode:
                updated = dict(step_results)
                updated["test_mode_approved"] = True
                updated["waiting_for_approval"] = False
                updated["_pipeline_pause"] = {"active": False, "reason": "test_mode"}
                ctx.task.step_results = updated
                ctx.db.commit()
                add_log(
                    ctx.db,
                    ctx.task,
                    "auto_mode: skipped TEST MODE pause after primary generation",
                )
            else:
                updated = dict(step_results)
                updated["waiting_for_approval"] = True
                updated["_pipeline_pause"] = {
                    "active": True,
                    "reason": "test_mode",
                    "message": "Test mode: review primary generation",
                }
                ctx.task.step_results = updated
                ctx.task.status = "processing"
                ctx.db.commit()
                add_log(ctx.db, ctx.task, "🛑 TEST MODE: Pausing after primary generation")
                return True

    if step_name == STEP_IMAGE_GEN:
        step_results = dict(ctx.task.step_results or {})
        pause_st = step_results.get("_pipeline_pause", {})
        if (
            isinstance(pause_st, dict)
            and pause_st.get("active")
            and pause_st.get("reason") == "image_review"
            and not step_results.get("_images_approved")
        ):
            if ctx.auto_mode:
                _auto_approve_images(ctx)
            else:
                return True
    return False


def _resolve_steps(ctx: PipelineContext) -> list[str]:
    if ctx.pipeline_steps is not None:
        steps = list(ctx.pipeline_steps)
    else:
        steps = (
            list(PIPELINE_PRESETS["full"])
            if ctx.use_serp
            else [STEP_PRIMARY_GEN, STEP_FINAL_EDIT, STEP_HTML_STRUCT, STEP_META_GEN]
        )

    if not pipeline_steps_use_serp(steps) and not ctx.task.outline:
        ctx.task.serp_data = ctx.task.serp_data or {}
        ctx.task.competitors_text = ctx.task.competitors_text or ""
        ctx.task.outline = {"final_outline": {"page_title": ctx.page_title, "sections": []}}
        ctx.outline_data = ctx.task.outline
        ctx.db.commit()
    return steps


def _persist_plan(ctx: PipelineContext, steps: list[str]) -> None:
    merged_plan = dict(ctx.task.step_results or {})
    merged_plan["_pipeline_plan"] = {"steps": steps}
    ctx.task.step_results = merged_plan
    ctx.db.commit()


def _preset_name(ctx: PipelineContext) -> str:
    if ctx.blueprint_page:
        return getattr(ctx.blueprint_page, "pipeline_preset", None) or "full"
    return "standalone"


def run_pipeline(db: Session, task_id: str, auto_mode: bool = False) -> None:
    ctx = PipelineContext(db, task_id, auto_mode=auto_mode)
    ctx.task.status = "processing"
    if ctx.task.total_cost is None:
        ctx.task.total_cost = 0.0
    db.commit()
    add_log(db, ctx.task, "🚀 Pipeline started / resumed")

    try:
        if _handle_pause_on_entry(ctx):
            return

        steps = _resolve_steps(ctx)
        _persist_plan(ctx, steps)
        add_log(db, ctx.task, f"Pipeline preset: {_preset_name(ctx)}, steps: {len(steps)}")

        for step_name in steps:
            step = STEP_REGISTRY.get(step_name)
            if not step:
                add_log(
                    db,
                    ctx.task,
                    f"⚠️ Unknown step '{step_name}' — skipped",
                    level="warn",
                    step=step_name,
                )
                continue
            _run_phase(ctx, step)
            if _handle_pause_after_step(ctx, step_name):
                return

        article = finalize_article(ctx)
        add_log(db, ctx.task, "✅ Pipeline finished successfully", step=None)
        notify_task_success(str(ctx.task.id), ctx.task.main_keyword, ctx.site_name, article.word_count)
    except Exception as e:
        db.rollback()
        if ctx.task.step_results:
            updated_steps = dict(ctx.task.step_results)
            for step_val in updated_steps.values():
                if isinstance(step_val, dict) and step_val.get("status") == "running":
                    step_val["status"] = "failed"
                    step_val["error"] = str(e)[:2000]
            ctx.task.step_results = updated_steps

        ctx.task.status = "failed"
        ctx.task.error_log = traceback.format_exc()
        db.commit()
        add_log(db, ctx.task, f"❌ Pipeline failed: {e!s}", level="error")
        notify_task_failed(str(ctx.task.id), ctx.task.main_keyword, str(e), ctx.site_name)
