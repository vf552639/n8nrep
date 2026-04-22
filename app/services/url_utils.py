"""URL normalization and merge helpers (competitor URLs for projects)."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(raw: str) -> str | None:
    s = (raw or "").strip()
    if not s:
        return None
    if "://" not in s:
        s = "https://" + s
    p = urlparse(s)
    if not p.netloc:
        return None
    return urlunparse((p.scheme, p.netloc, p.path or "", "", p.query, ""))


def domain_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def merge_urls_dedup_by_domain(primary: list[str], extra: list[str]) -> tuple[list[str], list[str]]:
    """
    Returns (merged, duplicates). `merged` preserves order: first all URLs from primary
    (deduped by domain), then extras whose domain was not seen. `duplicates` lists user
    URLs from `extra` dropped because their domain already appeared in `primary` or earlier
    in `extra`.
    """
    seen: set[str] = set()
    merged: list[str] = []
    for u in primary:
        d = domain_of(u)
        if d and d not in seen:
            seen.add(d)
            merged.append(u)
    duplicates: list[str] = []
    for u in extra:
        d = domain_of(u)
        if not d:
            continue
        if d in seen:
            duplicates.append(u)
            continue
        seen.add(d)
        merged.append(u)
    return merged, duplicates
