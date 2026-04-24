"""Sanitize external text before persistence (Postgres rejects NUL in TEXT/JSONB)."""


def strip_nul(value):
    """Recursively remove NUL (0x00) bytes from strings inside dict/list/str; passthrough for other types."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [strip_nul(item) for item in value]
    if isinstance(value, dict):
        return {k: strip_nul(v) for k, v in value.items()}
    return value
