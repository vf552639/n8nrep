import time
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._data: dict = {}

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._data[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


# Module-level singleton — shared across all callers in one process
_cache = TTLCache()
