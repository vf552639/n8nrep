import time
import pytest
from app.services.memory_cache import TTLCache


def test_set_and_get():
    cache = TTLCache()
    cache.set("k", {"x": 1}, ttl=60)
    assert cache.get("k") == {"x": 1}


def test_expired_returns_none():
    cache = TTLCache()
    cache.set("k", "val", ttl=0)
    time.sleep(0.01)
    assert cache.get("k") is None


def test_delete():
    cache = TTLCache()
    cache.set("k", "val", ttl=60)
    cache.delete("k")
    assert cache.get("k") is None


def test_missing_key_returns_none():
    cache = TTLCache()
    assert cache.get("nope") is None
