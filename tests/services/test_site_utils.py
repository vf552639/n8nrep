from __future__ import annotations

from app.models.site import Site
from app.services.site_utils import MARKUP_ONLY_SITE_KEY, brand_from_seed, is_markup_only_site


def test_brand_from_seed_title_cases_words() -> None:
    assert brand_from_seed("golden tiger") == "Golden Tiger"
    assert brand_from_seed("  MULTI  WORD  ") == "Multi Word"
    assert brand_from_seed("don't stop") == "Don't Stop"
    assert brand_from_seed("") == ""
    assert brand_from_seed(None) == ""


def test_is_markup_only_site_detects_reserved_name_or_domain() -> None:
    by_name = Site(name=MARKUP_ONLY_SITE_KEY, domain="example.com", country="DE", language="De")
    by_domain = Site(name="Some Site", domain=MARKUP_ONLY_SITE_KEY, country="DE", language="De")
    regular = Site(name="Site", domain="site.example", country="DE", language="De")

    assert is_markup_only_site(by_name) is True
    assert is_markup_only_site(by_domain) is True
    assert is_markup_only_site(regular) is False
    assert is_markup_only_site(None) is False
