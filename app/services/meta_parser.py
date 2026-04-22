"""
Extract title, description, H1 from meta_generation JSON (multiple LLM response shapes).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Markdown table parser
# ---------------------------------------------------------------------------

_HEADER_ALIASES: dict[str, str] = {
    "title": "title",
    "meta_title": "title",
    "description": "description",
    "meta_description": "description",
    "description (characters)": "description",
    "h1": "h1",
    "h1 (characters)": "h1",
    "heading": "h1",
    "headline": "h1",
    "psychological trigger": "trigger",
    "trigger": "trigger",
    "#": "number",
    "number": "number",
}


def _normalize_md_header(h: str) -> str:
    return _HEADER_ALIASES.get(h.strip().lower(), h.strip().lower())


def _parse_markdown_table(text: str) -> list[dict[str, str]]:
    """
    Parse a markdown table string into a list of dicts with normalised keys.

    Handles the LLM output pattern:
        | # | Title | Description (Characters) | H1 (Characters) | Psychological trigger |
        |---|-------|--------------------------|------------------|-----------------------|
        | 1 | Betty Casino: ... (48)    | Play 3000+ ...   | Betty Casino: ... (44) | Specificity |
    """
    lines = [ln for ln in text.strip().splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        return []

    def split_row(line: str) -> list[str]:
        return [c.strip() for c in line.split("|")[1:-1]]

    raw_headers = split_row(lines[0])
    headers = [_normalize_md_header(h) for h in raw_headers]

    rows: list[dict[str, str]] = []
    for line in lines[2:]:  # skip header + separator
        cells = split_row(line)
        if len(cells) < len(headers):
            continue
        row = {headers[i]: cells[i] for i in range(len(headers))}
        rows.append(row)
    return rows


def _try_parse_markdown_string(value: Any) -> list[dict[str, str]] | None:
    """Return parsed rows if *value* looks like a markdown table, else None."""
    if not isinstance(value, str) or "|" not in value:
        return None
    rows = _parse_markdown_table(value)
    return rows if rows else None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def meta_variant_list(meta_data: Any) -> list[Any]:
    """
    Return the variant list from any supported LLM response shape:

    1. List under  'variants' / 'results'  (any casing)       — standard JSON
    2. List under  'table'                                      — alternate key
    3. Markdown table string under  'response' / 'table'       — LLM returned prose table
    4. First non-empty list of dicts found among all values    — last resort
    """
    if not meta_data or not isinstance(meta_data, dict):
        return []

    by_lower: dict[str, Any] = {}
    for k, v in meta_data.items():
        if isinstance(k, str):
            by_lower.setdefault(k.lower(), v)

    # 1 & 2 — preferred list keys
    for preferred in ("results", "variants", "table"):
        v = by_lower.get(preferred)
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            return v
        # markdown table string under a known key
        if isinstance(v, str):
            rows = _try_parse_markdown_string(v)
            if rows:
                return rows

    # 3 — 'response' key often holds a markdown table string
    response_val = by_lower.get("response")
    if response_val is not None:
        rows = _try_parse_markdown_string(response_val)
        if rows:
            return rows

    # 4 — any list of dicts
    for val in meta_data.values():
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
            return list(val)

    return []


def _find_value(d: dict, *keys: str) -> str:
    """First non-empty string among keys (case-insensitive key match)."""
    lower_map: dict[str, Any] = {}
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


def extract_meta_from_parsed(meta_data: Any) -> dict[str, str]:
    """
    Extract title, description, h1 from any supported meta_generation JSON shape:
    flat dict, results[] / variants[] / table[] (any key casing),
    markdown table strings under 'response' / 'table', nested wrappers.
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
                description = description or _find_value(val, "description", "meta_description")
                h1 = h1 or _find_value(val, "h1", "heading", "headline")
                if title:
                    break

    return {"title": title, "description": description, "h1": h1}


# Alias for callers that follow the original spec name
_extract_meta_from_parsed = extract_meta_from_parsed
