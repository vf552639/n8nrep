import json

from app.config import settings
from app.services.image_utils import _extract_multimedia_from_text_content, extract_multimedia_blocks
from app.services.json_parser import clean_and_parse_json
from app.services.pipeline.llm_client import call_agent
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline.template_vars import setup_template_vars
from app.services.pipeline_constants import STEP_FINAL_ANALYSIS, STEP_IMAGE_PROMPT_GEN


class ImagePromptsStep:
    name = STEP_IMAGE_PROMPT_GEN
    policy = StepPolicy()

    def run(self, ctx) -> StepResult:
        if not settings.IMAGE_GEN_ENABLED:
            add_log(
                ctx.db, ctx.task, "Image generation disabled globally — skipping", step=STEP_IMAGE_PROMPT_GEN
            )
            return StepResult(status="completed", result=json.dumps({"images": [], "skipped": True}))

        outline_raw = ctx.task.step_results.get(STEP_FINAL_ANALYSIS, {}).get("result", "")
        if not outline_raw:
            add_log(
                ctx.db,
                ctx.task,
                "No final structure found — skipping image prompt gen",
                step=STEP_IMAGE_PROMPT_GEN,
            )
            return StepResult(status="completed", result=json.dumps({"images": []}))

        outline_json = clean_and_parse_json(outline_raw)
        multimedia_blocks = extract_multimedia_blocks(outline_json)
        outline_raw_str = str(outline_raw)
        if not multimedia_blocks and outline_raw_str and len(outline_raw_str) > 100:
            text_blocks = _extract_multimedia_from_text_content(outline_raw_str, "outline_raw")
            if text_blocks:
                for i, tb in enumerate(text_blocks, start=1):
                    tb["id"] = f"img_{i}"
                multimedia_blocks = text_blocks
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Found {len(text_blocks)} MULTIMEDIA block(s) via raw text fallback (not in JSON keys)",
                    level="info",
                    step=STEP_IMAGE_PROMPT_GEN,
                )

        if not multimedia_blocks:
            outline_snippet = outline_raw_str[:1500] if outline_raw_str else "EMPTY"
            add_log(
                ctx.db,
                ctx.task,
                f"[DEBUG] No MULTIMEDIA found anywhere. Outline snippet (first 1500 chars): {outline_snippet}",
                level="warn",
                step=STEP_IMAGE_PROMPT_GEN,
            )
            add_log(
                ctx.db,
                ctx.task,
                "⚠️ No MULTIMEDIA blocks in outline. Возможные причины: "
                "1) промпт final_structure_analysis не генерирует поле MULTIMEDIA/multimedia в секциях; "
                "2) несоответствие регистра ключа в JSON. "
                "Проверь step_results['final_structure_analysis'] вручную.",
                level="warn",
                step=STEP_IMAGE_PROMPT_GEN,
            )
            add_log(
                ctx.db,
                ctx.task,
                "No MULTIMEDIA blocks found in outline — skipping",
                step=STEP_IMAGE_PROMPT_GEN,
            )
            return StepResult(status="completed", result=json.dumps({"images": []}))

        type_map = {
            "infographie": "Infographic",
            "infographie procedurale": "Infographic",
            "infographie procédurale": "Infographic",
            "tableau html": "Image",
            "tableau de donnees": "Image",
            "tableau de données": "Image",
            "tableau recapitulatif": "Image",
            "tableau récapitulatif": "Image",
            "tableau comparatif": "Image",
            "bouton d'action": "Image",
            "bouton d'action (cta)": "Image",
            "schema de processus": "Infographic",
            "schéma de processus": "Infographic",
            "infographic": "Infographic",
            "image": "Image",
            "chart": "Image",
            "table": "Image",
            "diagram": "Infographic",
        }

        def _norm_mm_type(block: dict) -> str:
            mm = block.get("multimedia", {}) if isinstance(block, dict) else {}
            t = mm.get("Type") or mm.get("type") or ""
            return type_map.get(str(t).strip().lower(), "")

        def _extract_prompt_fallback(data) -> str:
            if not isinstance(data, dict):
                return ""
            for key in (
                "image_prompt",
                "midjourney_prompt",
                "prompt",
                "mj_prompt",
                "visual_prompt",
                "description",
            ):
                val = data.get(key)
                if val and isinstance(val, str) and len(val.strip()) > 20:
                    return val.strip()
            for val in data.values():
                if isinstance(val, str) and len(val.strip()) > 50:
                    return val.strip()
            for val in data.values():
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            nested = _extract_prompt_fallback(item)
                            if nested:
                                return nested
            for val in data.values():
                if isinstance(val, dict):
                    nested = _extract_prompt_fallback(val)
                    if nested:
                        return nested
            return ""

        generatable_types = {"Image", "Infographic"}
        normalized_types = [(_norm_mm_type(b) or "Image") for b in multimedia_blocks]
        eligible_blocks = [b for b in multimedia_blocks if (_norm_mm_type(b) or "Image") in generatable_types]
        skipped_count = len(multimedia_blocks) - len(eligible_blocks)
        add_log(
            ctx.db,
            ctx.task,
            f"Outline parsed. Total MULTIMEDIA blocks found: {len(multimedia_blocks)}. "
            f"Eligible (Image/Infographic): {len(eligible_blocks)}, skipped (other types): {skipped_count}. "
            f"Types found: {normalized_types}",
            step=STEP_IMAGE_PROMPT_GEN,
        )
        if not eligible_blocks:
            add_log(
                ctx.db,
                ctx.task,
                "MULTIMEDIA blocks found, but no generatable types (Image/Infographic) — skipping",
                step=STEP_IMAGE_PROMPT_GEN,
            )
            return StepResult(status="completed", result=json.dumps({"images": []}))

        add_log(
            ctx.db,
            ctx.task,
            f"Found {len(multimedia_blocks)} MULTIMEDIA blocks, eligible: {len(eligible_blocks)}, skipped: {skipped_count}. Generating prompts...",
            step=STEP_IMAGE_PROMPT_GEN,
        )

        setup_template_vars(ctx)
        images = []
        total_cost = 0.0
        actual_model = None
        last_resolved_prompts = None
        last_variables_snapshot = None

        for idx, block in enumerate(eligible_blocks, start=1):
            mm = block.get("multimedia", {}) if isinstance(block, dict) else {}
            mm_type = _norm_mm_type(block) or "Image"
            description = str(mm.get("Description") or mm.get("description") or "").strip()
            purpose = str(mm.get("Purpose") or mm.get("purpose") or "").strip()
            location = str(mm.get("Location") or mm.get("location") or "").strip() or f"image_{idx}"
            parent_title = str(block.get("section") or "").strip() or "Untitled Section"
            block_vars = dict(ctx.template_vars or {})
            block_vars.update(
                {
                    "type": mm_type,
                    "description": description,
                    "purpose": purpose,
                    "parent_title": parent_title,
                    "location": location,
                }
            )
            block_context = f"MULTIMEDIA block payload:\n{json.dumps(block, ensure_ascii=False, indent=2)}"
            try:
                (
                    block_result_json,
                    block_cost,
                    block_model,
                    block_resolved_prompts,
                    block_variables_snapshot,
                ) = call_agent(
                    ctx,
                    "image_prompt_generation",
                    block_context,
                    response_format={"type": "json_object"},
                    variables=block_vars,
                )
                total_cost += block_cost
                actual_model = block_model
                last_resolved_prompts = block_resolved_prompts
                last_variables_snapshot = block_variables_snapshot
                parsed = clean_and_parse_json(block_result_json)
                if not isinstance(parsed, dict):
                    parsed = {}
                midjourney_prompt = _extract_prompt_fallback(parsed)
                if not midjourney_prompt:
                    raw_snip = str(block_result_json)[:500]
                    add_log(
                        ctx.db,
                        ctx.task,
                        f"[DEBUG] Image prompt raw response for {block.get('id', f'img_{idx}')}: {raw_snip}",
                        level="warn",
                        step=STEP_IMAGE_PROMPT_GEN,
                    )
                    add_log(
                        ctx.db,
                        ctx.task,
                        f"Image prompt gen returned empty prompt for block {block.get('id', f'img_{idx}')}; block skipped",
                        level="warn",
                        step=STEP_IMAGE_PROMPT_GEN,
                    )
                    continue
                mj = str(midjourney_prompt).strip()
                images.append(
                    {
                        "id": block.get("id", f"img_{idx}"),
                        "section": parent_title,
                        "location": location,
                        "type": mm_type,
                        "description": description,
                        "purpose": purpose,
                        "image_prompt": mj,
                        "midjourney_prompt": mj,
                        "alt_text": str(parsed.get("alt_text") or f"{mm_type} for {parent_title}").strip(),
                        "aspect_ratio": str(parsed.get("aspect_ratio") or "16:9").strip(),
                    }
                )
            except Exception as e:
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Failed image prompt generation for block {block.get('id', f'img_{idx}')}: {e}",
                    level="error",
                    step=STEP_IMAGE_PROMPT_GEN,
                )

        if len(images) == 0 and len(eligible_blocks) > 0:
            add_log(
                ctx.db,
                ctx.task,
                "No prompts built in primary pass. Running simplified fallback prompt extraction...",
                level="warn",
                step=STEP_IMAGE_PROMPT_GEN,
            )
            for idx, block in enumerate(eligible_blocks, start=1):
                mm = block.get("multimedia", {}) if isinstance(block, dict) else {}
                mm_type = _norm_mm_type(block) or "Image"
                description = str(mm.get("Description") or mm.get("description") or "").strip()
                parent_title = str(block.get("section") or "").strip() or "Untitled Section"
                purpose = str(mm.get("Purpose") or mm.get("purpose") or "").strip()
                location = str(mm.get("Location") or mm.get("location") or "").strip() or f"image_{idx}"
                if not description:
                    description = f"{mm_type} for section '{parent_title}'"
                fallback_context = (
                    f"Create an AI image generation prompt for: {description}. "
                    "Respond ONLY with JSON: "
                    '{"image_prompt": "<detailed English prompt>", '
                    '"alt_text": "<short alt text>", "aspect_ratio": "16:9"}'
                )
                try:
                    fallback_json, fb_cost, fb_model, fb_resolved_prompts, fb_variables_snapshot = call_agent(
                        ctx,
                        "image_prompt_generation",
                        fallback_context,
                        response_format={"type": "json_object"},
                        variables=ctx.template_vars,
                    )
                    total_cost += fb_cost
                    actual_model = fb_model
                    last_resolved_prompts = fb_resolved_prompts
                    last_variables_snapshot = fb_variables_snapshot
                    parsed_fb = clean_and_parse_json(fallback_json)
                    if not isinstance(parsed_fb, dict):
                        parsed_fb = {}
                    fallback_prompt = _extract_prompt_fallback(parsed_fb)
                    if not fallback_prompt:
                        add_log(
                            ctx.db,
                            ctx.task,
                            f"Fallback empty prompt for block {block.get('id', f'img_{idx}')}. Raw: {str(fallback_json)[:500]}",
                            level="warn",
                            step=STEP_IMAGE_PROMPT_GEN,
                        )
                        continue
                    fb = str(fallback_prompt).strip()
                    images.append(
                        {
                            "id": block.get("id", f"img_{idx}"),
                            "section": parent_title,
                            "location": location,
                            "type": mm_type,
                            "description": description,
                            "purpose": purpose,
                            "image_prompt": fb,
                            "midjourney_prompt": fb,
                            "alt_text": str(
                                parsed_fb.get("alt_text") or f"{mm_type} for {parent_title}"
                            ).strip(),
                            "aspect_ratio": str(parsed_fb.get("aspect_ratio") or "16:9").strip(),
                        }
                    )
                except Exception as e:
                    add_log(
                        ctx.db,
                        ctx.task,
                        f"Fallback image prompt generation failed for block {block.get('id', f'img_{idx}')}: {e}",
                        level="error",
                        step=STEP_IMAGE_PROMPT_GEN,
                    )

        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + total_cost
        result_json = json.dumps({"images": images}, ensure_ascii=False)
        add_log(
            ctx.db,
            ctx.task,
            f"Image prompt generation completed: {len(images)} prompts built",
            step=STEP_IMAGE_PROMPT_GEN,
        )
        return StepResult(
            status="completed",
            result=result_json,
            model=actual_model,
            cost=total_cost,
            variables_snapshot=last_variables_snapshot,
            resolved_prompts=last_resolved_prompts,
        )


register_step(ImagePromptsStep())
