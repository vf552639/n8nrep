"""Tests for app.services.url_utils."""

import pytest

from app.services.url_utils import domain_of, merge_urls_dedup_by_domain, normalize_url


def test_normalize_url_empty():
    assert normalize_url("") is None
    assert normalize_url("   ") is None


def test_normalize_url_adds_scheme():
    assert normalize_url("example.com/foo") == "https://example.com/foo"
    assert normalize_url("HTTPS://Example.COM/path?q=1") == "https://Example.COM/path?q=1"


def test_normalize_url_invalid():
    assert normalize_url("://nope") is None
    assert normalize_url("/only/path") is None


def test_domain_of_strips_www():
    assert domain_of("https://www.EXAMPLE.com/a") == "example.com"
    assert domain_of("https://blog.example.com/") == "blog.example.com"


def test_merge_empty_primary():
    merged, dups = merge_urls_dedup_by_domain([], ["https://a.com", "https://b.com"])
    assert merged == ["https://a.com", "https://b.com"]
    assert dups == []


def test_merge_empty_extra():
    merged, dups = merge_urls_dedup_by_domain(["https://x.com"], [])
    assert merged == ["https://x.com"]
    assert dups == []


def test_merge_www_same_domain():
    primary = ["https://www.example.com/page1"]
    extra = ["https://example.com/other"]
    merged, dups = merge_urls_dedup_by_domain(primary, extra)
    assert merged == primary
    assert dups == ["https://example.com/other"]


def test_merge_different_path_same_domain_from_extra():
    primary = ["https://site.org/a"]
    extra = ["https://site.org/b", "https://new.net/"]
    merged, dups = merge_urls_dedup_by_domain(primary, extra)
    assert merged == ["https://site.org/a", "https://new.net/"]
    assert dups == ["https://site.org/b"]


def test_merge_skips_bad_extra_urls():
    merged, dups = merge_urls_dedup_by_domain(["https://ok.test/"], ["not-a-url", "https://other.test/"])
    assert merged == ["https://ok.test/", "https://other.test/"]
    assert dups == []


def test_merge_preserves_primary_order_dedup_primary():
    merged, dups = merge_urls_dedup_by_domain(
        ["https://dup.com/1", "https://dup.com/2", "https://z.com/"],
        ["https://extra.com/"],
    )
    assert merged == ["https://dup.com/1", "https://z.com/", "https://extra.com/"]
    assert dups == []


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  https://trimmed.com/  ", "https://trimmed.com/"),
    ],
)
def test_normalize_url_trim(raw, expected):
    assert normalize_url(raw) == expected
