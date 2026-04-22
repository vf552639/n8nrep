import hashlib
import json
from collections.abc import Callable
from typing import Any

from app.config import settings


def _get_redis_client():
    if not settings.SERP_CACHE_ENABLED:
        return None
    try:
        import redis  # type: ignore
    except Exception:
        return None
    try:
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _safe_json_loads(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _serp_cache_key(
    keyword: str, country_code: str, language_code: str, serp_config: dict | None = None
) -> str:
    cfg = serp_config or {}
    engine = str(cfg.get("search_engine", "google")).lower()
    kw_hash = hashlib.sha256(keyword.lower().strip().encode("utf-8")).hexdigest()
    return f"serp_cache:{kw_hash}:{country_code.lower()}:{language_code.lower()}:{engine}"


def invalidate_serp_cache(
    keyword: str, country_code: str, language_code: str, serp_config: dict | None = None
) -> bool:
    client = _get_redis_client()
    if not client:
        return False
    key = _serp_cache_key(keyword, country_code, language_code, serp_config)
    try:
        return bool(client.delete(key))
    except Exception:
        return False


def get_cached_serp(
    keyword: str,
    country_code: str,
    language_code: str,
    serp_config: dict | None,
    fetch_fn: Callable[[str, str, str, dict | None], dict[str, Any]],
    force_refresh: bool = False,
) -> dict[str, Any]:
    client = _get_redis_client()
    key = _serp_cache_key(keyword, country_code, language_code, serp_config)

    if client and not force_refresh:
        try:
            cached = _safe_json_loads(client.get(key))
            if cached is not None:
                cached["_from_cache"] = True
                return cached
        except Exception:
            pass

    result = fetch_fn(keyword, country_code, language_code, serp_config)
    if not isinstance(result, dict):
        return result

    result.setdefault("_from_cache", False)

    if client:
        try:
            client.setex(key, int(settings.SERP_CACHE_TTL), json.dumps(result, ensure_ascii=False))
        except Exception:
            pass
    return result


def _scrape_cache_key(url: str) -> str:
    return f"scrape_cache:{hashlib.sha256(url.strip().encode('utf-8')).hexdigest()}"


def get_cached_scrape_item(url: str) -> dict | None:
    client = _get_redis_client()
    if not client:
        return None
    try:
        return _safe_json_loads(client.get(_scrape_cache_key(url)))
    except Exception:
        return None


def set_cached_scrape_item(url: str, parsed_data: dict) -> None:
    client = _get_redis_client()
    if not client:
        return
    try:
        client.setex(
            _scrape_cache_key(url),
            int(settings.SCRAPE_CACHE_TTL),
            json.dumps(parsed_data, ensure_ascii=False),
        )
    except Exception:
        return


def get_cached_scrape(
    urls_list: list[str], scrape_fn: Callable[[list[str]], dict[str, dict]]
) -> dict[str, Any]:
    """Generic batch wrapper for per-URL scrape cache.

    scrape_fn should return mapping: {url: {"text": "...", "word_count": N, "headers": {...}, ...}}
    """
    cache_hits = 0
    cache_misses = 0
    by_url: dict[str, dict] = {}
    misses: list[str] = []

    for url in urls_list:
        cached = get_cached_scrape_item(url)
        if cached:
            cache_hits += 1
            by_url[url] = cached
        else:
            cache_misses += 1
            misses.append(url)

    if misses:
        fetched_map = scrape_fn(misses) or {}
        for url, payload in fetched_map.items():
            if isinstance(payload, dict):
                by_url[url] = payload
                set_cached_scrape_item(url, payload)

    return {"items": by_url, "cache_hits": cache_hits, "cache_misses": cache_misses}
