"""Image generation step implementation.

This module is responsible for generating and uploading images.
Pause/resume auto-approval orchestration lives in `pipeline/runner.py`.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config import settings
from app.services.image_generator import ImageResult, OpenRouterImageGenerator, resolve_image_generation_model
from app.services.image_hosting import ImgBBUploader
from app.services.json_parser import clean_and_parse_json
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline_constants import STEP_IMAGE_GEN, STEP_IMAGE_PROMPT_GEN


class ImageGenStep:
    name = STEP_IMAGE_GEN
    policy = StepPolicy()

    def run(self, ctx) -> StepResult:
        if not settings.IMAGE_GEN_ENABLED:
            add_log(ctx.db, ctx.task, "Image generation disabled — skipping", step=STEP_IMAGE_GEN)
            return StepResult(status="completed", result=json.dumps({"images": [], "skipped": True}))
        if not settings.OPENROUTER_API_KEY:
            add_log(
                ctx.db,
                ctx.task,
                "❌ OPENROUTER_API_KEY не задан — image generation невозможен. Тот же ключ, что для LLM.",
                level="error",
                step=STEP_IMAGE_GEN,
            )
            return StepResult(
                status="failed", result=json.dumps({"images": [], "error": "OPENROUTER_API_KEY missing"})
            )
        if not settings.IMGBB_API_KEY:
            add_log(
                ctx.db,
                ctx.task,
                "❌ IMGBB_API_KEY не задан — загрузка изображений невозможна. Заполни в Settings.",
                level="error",
                step=STEP_IMAGE_GEN,
            )
            return StepResult(
                status="failed", result=json.dumps({"images": [], "error": "IMGBB_API_KEY missing"})
            )

        prompt_data_raw = ctx.task.step_results.get(STEP_IMAGE_PROMPT_GEN, {}).get("result", "")
        prompt_data = clean_and_parse_json(prompt_data_raw) if prompt_data_raw else {}
        images_to_gen = prompt_data.get("images", []) if isinstance(prompt_data, dict) else []
        if not images_to_gen or (isinstance(prompt_data, dict) and prompt_data.get("skipped")):
            add_log(ctx.db, ctx.task, "No image prompts to process — skipping", step=STEP_IMAGE_GEN)
            return StepResult(status="completed", result=json.dumps({"images": []}))

        model_id = resolve_image_generation_model(ctx.db)
        fallback_model = settings.IMAGE_MODEL_DEFAULT if model_id != settings.IMAGE_MODEL_DEFAULT else None
        add_log(
            ctx.db,
            ctx.task,
            f"Starting OpenRouter image generation for {len(images_to_gen)} image(s), model={model_id}...",
            step=STEP_IMAGE_GEN,
        )

        uploader = ImgBBUploader(api_key=settings.IMGBB_API_KEY)
        keyword_slug = ctx.task.main_keyword.lower().replace(" ", "-")[:30]
        site_slug = ctx.site_name.lower().replace(" ", "-")[:20]

        def _prompt_text(img: dict) -> str:
            return (img.get("image_prompt") or img.get("midjourney_prompt") or "").strip()

        def _run_one(img: dict) -> tuple[dict, ImageResult]:
            gen = OpenRouterImageGenerator(
                api_key=settings.OPENROUTER_API_KEY,
                model=model_id,
                fallback_model=fallback_model,
            )
            text = _prompt_text(img)
            if not text:
                return img, ImageResult(status="failed", error="Empty image prompt")
            return img, gen.generate_and_wait(text, aspect_ratio=img.get("aspect_ratio", "16:9"))

        images_result = []
        max_workers = min(4, max(1, len(images_to_gen)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_one, img): img for img in images_to_gen}
            for fut in as_completed(futures):
                img = futures[fut]
                try:
                    img, result = fut.result()
                except Exception as e:
                    pt = _prompt_text(img)
                    images_result.append(
                        {
                            "id": img.get("id"),
                            "section": img.get("section", ""),
                            "image_prompt": pt,
                            "midjourney_prompt": pt,
                            "alt_text": img.get("alt_text", ""),
                            "provider_task_id": "",
                            "status": "failed",
                            "original_url": None,
                            "hosted_url": None,
                            "approved": None,
                            "error": str(e),
                        }
                    )
                    add_log(ctx.db, ctx.task, f"❌ {img.get('id')}: {e}", level="warn", step=STEP_IMAGE_GEN)
                    continue

                pt = _prompt_text(img)
                row = {
                    "id": img.get("id"),
                    "section": img.get("section", ""),
                    "image_prompt": pt,
                    "midjourney_prompt": pt,
                    "alt_text": img.get("alt_text", ""),
                    "provider_task_id": "openrouter-sync",
                    "original_url": None,
                    "hosted_url": None,
                    "approved": None,
                    "error": None,
                }
                if result.status == "completed" and result.image_url:
                    try:
                        filename = f"{site_slug}_{keyword_slug}_{img.get('id', 'img')}"
                        hosted = uploader.upload_from_data_url(result.image_url, filename)
                        row["status"] = "completed"
                        row["hosted_url"] = hosted.get("url", "")
                        add_log(
                            ctx.db,
                            ctx.task,
                            f"✅ {img.get('id')} → {row['hosted_url'][:60] if row['hosted_url'] else 'ok'}",
                            step=STEP_IMAGE_GEN,
                        )
                    except Exception as e:
                        row["status"] = "failed"
                        row["error"] = str(e)
                        add_log(
                            ctx.db,
                            ctx.task,
                            f"❌ {img.get('id')} ImgBB: {e}",
                            level="warn",
                            step=STEP_IMAGE_GEN,
                        )
                else:
                    row["status"] = "failed"
                    row["error"] = result.error or "Image generation failed"
                    add_log(
                        ctx.db,
                        ctx.task,
                        f"❌ {img.get('id')}: {row['error']}",
                        level="warn",
                        step=STEP_IMAGE_GEN,
                    )
                images_result.append(row)

        completed_count = sum(1 for im in images_result if im["status"] == "completed")
        failed_count = sum(1 for im in images_result if im["status"] == "failed")
        result_payload = {
            "images": images_result,
            "summary": {"total": len(images_result), "completed": completed_count, "failed": failed_count},
            "model": model_id,
        }

        if completed_count > 0 or failed_count > 0:
            step_results = dict(ctx.task.step_results or {})
            step_results["_pipeline_pause"] = {
                "active": True,
                "reason": "image_review",
                "message": "Waiting for image review",
            }
            ctx.task.step_results = step_results
            ctx.task.status = "processing"
            ctx.db.commit()
            add_log(
                ctx.db,
                ctx.task,
                f"🖼️ Image generation done: {completed_count} ok, {failed_count} failed. Waiting for review.",
                step=STEP_IMAGE_GEN,
            )
        else:
            add_log(ctx.db, ctx.task, "No images generated — continuing pipeline", step=STEP_IMAGE_GEN)

        return StepResult(status="completed", result=json.dumps(result_payload, ensure_ascii=False))


register_step(ImageGenStep())
