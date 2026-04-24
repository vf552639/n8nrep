from __future__ import annotations

import string

from app.models.site import Site

MARKUP_ONLY_SITE_KEY = "__markup_only__"


def is_markup_only_site(site: Site | None) -> bool:
    return bool(site) and (
        site.name == MARKUP_ONLY_SITE_KEY or site.domain == MARKUP_ONLY_SITE_KEY
    )


def brand_from_seed(seed_keyword: str | None) -> str:
    """Build display brand from seed phrase (e.g. "golden tiger" -> "Golden Tiger")."""
    return string.capwords((seed_keyword or "").strip())
