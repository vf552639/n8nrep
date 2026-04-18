"""Normalize language strings for storage (aligned with SQL INITCAP(TRIM(...)))."""


def normalize_language(value: str | None) -> str | None:
    """
    Trim and apply title-case per whitespace-separated word (same idea as PostgreSQL INITCAP).
    Examples: "french" -> "French", "ENGLISH" -> "English", "  german " -> "German".
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return ""
    parts = stripped.split()
    return " ".join((p[:1].upper() + p[1:].lower()) if p else "" for p in parts)
