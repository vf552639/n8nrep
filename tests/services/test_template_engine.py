"""Tests for ensure_head_meta and render_author_footer."""

from __future__ import annotations

import re

from app.models.author import Author
from app.services.template_engine import ensure_head_meta, render_author_footer


def test_ensure_head_meta_wraps_fragment():
    html = "<div>Hello</div>"
    out = ensure_head_meta(html, "T1", "D1")
    assert "<!doctype html>" in out.lower()
    assert "<html>" in out.lower()
    assert "<head>" in out.lower()
    assert "<title>T1</title>" in out
    assert '<meta name="description" content="D1">' in out
    assert "<div>Hello</div>" in out


def test_ensure_head_meta_updates_title_in_full_document():
    html = "<!DOCTYPE html><html><head><title>old</title></head><body>x</body></html>"
    out = ensure_head_meta(html, "New Title", "")
    assert "<title>New Title</title>" in out
    assert out.count("<title>") == 1


def test_ensure_head_meta_inserts_meta_description_when_missing():
    html = "<!DOCTYPE html><html><head><title>x</title></head><body></body></html>"
    out = ensure_head_meta(html, "x", "Desc here")
    assert 'name="description"' in out
    assert "Desc here" in out


def test_ensure_head_meta_idempotent():
    frag = "<p>Hi</p>"
    once = ensure_head_meta(frag, "A", "B")
    twice = ensure_head_meta(once, "A", "B")
    assert twice.count("<title>A</title>") == 1
    assert len(re.findall(r'name="description"', twice)) == 1


def test_ensure_head_meta_escapes_special_chars():
    out = ensure_head_meta("<div/>", 'Tom & Jerry "best"', "Line1\nLine2 <script>")
    assert "Tom &amp; Jerry" in out or "&amp;" in out
    assert "<script>" not in out or "&lt;script&gt;" in out


def test_ensure_head_meta_empty_title_skips_title_tag_in_fragment():
    out = ensure_head_meta("<div/>", "", "OnlyDesc")
    assert "<title>" not in out
    assert "OnlyDesc" in out


def test_render_author_footer_full_order():
    a = Author()
    a.author = "Jane"
    a.country_full = "Germany"
    a.co_short = "DE"
    a.city = "Berlin"
    a.language = "De"
    a.bio = "Writer"
    html = render_author_footer(a)
    assert "Jane" in html
    assert "Germany" in html
    assert "DE" in html
    assert "Berlin" in html
    assert "Writer" in html
    # order: Автор, Страна, Код страны, Город, Язык, Биография
    pos = [
        html.index("Автор"),
        html.index("Страна"),
        html.index("Код страны"),
        html.index("Город"),
        html.index("Язык"),
        html.index("Биография"),
    ]
    assert pos == sorted(pos)


def test_render_author_footer_all_none():
    a = Author()
    assert render_author_footer(a) == ""


def test_render_author_footer_escapes_bio():
    a = Author()
    a.author = "X"
    a.bio = "<b>bad</b> &"
    html = render_author_footer(a)
    assert "<b>bad</b>" not in html
    assert "&lt;b&gt;bad&lt;/b&gt;" in html
    assert "&amp;" in html


def test_render_author_footer_none_author():
    assert render_author_footer(None) == ""
