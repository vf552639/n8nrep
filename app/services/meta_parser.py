"""
Extract title, description, H1 from meta_generation JSON (multiple LLM response shapes).
"""
from __future__ import annotations

from typing import Any, Dict, List


def meta_variant_list(meta_data: Any) -> List[Any]:
    """
    Prefer list under 'results' or 'variants' (case-insensitive); else first non-empty list of dicts.
    Used for DOCX multi-variant expansion.
    """
    if not meta_data or not isinstance(meta_data, dict):
        return []
    by_lower: Dict[str, Any] = {}
    for k, v in meta_data.items():
        if isinstance(k, str):
            by_lower.setdefault(k.lower(), v)
    for preferred in ("results", "variants"):
        v = by_lower.get(preferred)
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            return v
    for val in meta_data.values():
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
            return list(val)
    return []


def _find_value(d: dict, *keys: str) -> str:
    """First non-empty string among keys (case-insensitive key match)."""
    lower_map: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(k, str):
            lk = k.lower()
            if lk not in lower_map:
                lower_map[lk] = v
    for key in keys:
        val = lower_map.get(key.lower())
        if val is None:
            continue
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, bool):
            continue
        if isinstance(val, (int, float)):
            s = str(val).strip()
            if s:
                return s
    return ""


def extract_meta_from_parsed(meta_data: Any) -> Dict[str, str]:
    """
    Extract title, description, h1 from any supported meta_generation JSON shape:
    flat dict, results[] / variants[] (any key casing), nested wrappers (e.g. response).
    """
    if not meta_data or not isinstance(meta_data, dict):
        return {"title": "", "description": "", "h1": ""}

    title = ""
    description = ""
    h1 = ""

    variant_list = meta_variant_list(meta_data)
    if variant_list:
        first = variant_list[0]
        if isinstance(first, dict):
            title = _find_value(first, "title", "meta_title")
            description = _find_value(first, "description", "meta_description")
            h1 = _find_value(first, "h1", "heading", "headline")

    if not title:
        title = _find_value(meta_data, "title", "meta_title")
        description = description or _find_value(meta_data, "description", "meta_description")
        h1 = h1 or _find_value(meta_data, "h1", "heading", "headline")

    if not title:
        for val in meta_data.values():
            if isinstance(val, dict):
                title = _find_value(val, "title", "meta_title")
                description = description or _find_value(
                    val, "description", "meta_description"
                )
                h1 = h1 or _find_value(val, "h1", "heading", "headline")
                if title:
                    break

    return {"title": title, "description": description, "h1": h1}


# Alias for callers that follow the original spec name
_extract_meta_from_parsed = extract_meta_from_parsed
