"""
Pipeline preset definitions and resolver for blueprint pages.
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.services.pipeline_constants import (
    STEP_SERP,
    STEP_SCRAPING,
    STEP_AI_ANALYSIS,
    STEP_CHUNK_ANALYSIS,
    STEP_COMP_STRUCTURE,
    STEP_FINAL_ANALYSIS,
    STEP_STRUCTURE_FACT_CHECK,
    STEP_PRIMARY_GEN,
    STEP_PRIMARY_GEN_ABOUT,
    STEP_PRIMARY_GEN_LEGAL,
    STEP_COMP_COMPARISON,
    STEP_READER_OPINION,
    STEP_IMPROVER,
    STEP_FINAL_EDIT,
    STEP_HTML_STRUCT,
    STEP_META_GEN,
)

PIPELINE_PRESETS: dict[str, List[str]] = {
    "full": [
        STEP_SERP,
        STEP_SCRAPING,
        STEP_AI_ANALYSIS,
        STEP_CHUNK_ANALYSIS,
        STEP_COMP_STRUCTURE,
        STEP_FINAL_ANALYSIS,
        STEP_STRUCTURE_FACT_CHECK,
        STEP_PRIMARY_GEN,
        STEP_COMP_COMPARISON,
        STEP_READER_OPINION,
        STEP_IMPROVER,
        STEP_FINAL_EDIT,
        STEP_HTML_STRUCT,
        STEP_META_GEN,
    ],
    "category": [
        STEP_SERP,
        STEP_SCRAPING,
        STEP_FINAL_ANALYSIS,
        STEP_PRIMARY_GEN,
        STEP_FINAL_EDIT,
        STEP_HTML_STRUCT,
        STEP_META_GEN,
    ],
    "about": [
        STEP_PRIMARY_GEN_ABOUT,
        STEP_META_GEN,
    ],
    "legal": [
        STEP_PRIMARY_GEN_LEGAL,
        STEP_META_GEN,
    ],
}

SERP_STEPS = {STEP_SERP, STEP_SCRAPING}

VALID_PRESETS = frozenset(PIPELINE_PRESETS.keys()) | {"custom"}


def resolve_steps_from_payload(
    pipeline_preset: str,
    pipeline_steps_custom: Optional[Any],
) -> List[str]:
    preset = (pipeline_preset or "full").strip().lower()
    if preset not in VALID_PRESETS:
        preset = "full"
    if preset == "custom":
        if isinstance(pipeline_steps_custom, list) and len(pipeline_steps_custom) > 0:
            return [str(s) for s in pipeline_steps_custom]
        return list(PIPELINE_PRESETS["full"])
    return list(PIPELINE_PRESETS.get(preset, PIPELINE_PRESETS["full"]))


def resolve_pipeline_steps(blueprint_page: Any) -> List[str]:
    if blueprint_page is None:
        return list(PIPELINE_PRESETS["full"])
    preset = getattr(blueprint_page, "pipeline_preset", None) or "full"
    custom = getattr(blueprint_page, "pipeline_steps_custom", None)
    return resolve_steps_from_payload(str(preset), custom)


def pipeline_steps_use_serp(steps: List[str]) -> bool:
    return bool(SERP_STEPS.intersection(steps))


def preset_uses_serp(preset: str) -> bool:
    steps = PIPELINE_PRESETS.get(preset, [])
    return bool(SERP_STEPS.intersection(steps))


def get_primary_gen_agent(steps: List[str]) -> str:
    for step in steps:
        if step.startswith("primary_generation"):
            return step
    return STEP_PRIMARY_GEN
