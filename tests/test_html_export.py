"""Tests for app.services.html_export.clean_html_for_paste."""

from app.services.html_export import clean_html_for_paste


def test_clean_full_document_strips_wrapper_keeps_comment_and_content():
    inp = (
        "<!DOCTYPE html><html><head><title>x</title></head>"
        "<body><h1>t</h1><!-- MEDIA: IMAGE: foo --><p>x</p></body></html>"
    )
    out = clean_html_for_paste(inp)
    assert "<h1>t</h1>" in out
    assert "<!-- MEDIA: IMAGE: foo -->" in out
    assert "<p>x</p>" in out
    assert "<!DOCTYPE" not in out
    assert "<html" not in out.lower()
    assert "<head" not in out.lower()
    assert "<title" not in out.lower()


def test_clean_fragment_unchanged_except_obvious_chrome():
    inp = "<p>hello</p><script>evil()</script>"
    out = clean_html_for_paste(inp)
    assert "<p>hello</p>" in out
    assert "script" not in out.lower()
    assert "evil" not in out


def test_comment_with_backticks_preserved():
    inp = "<!-- MEDIA: Format: `<figure>...</figure>` -->"
    out = clean_html_for_paste(inp)
    assert "<!-- MEDIA: Format: `<figure>...</figure>` -->" in out


def test_mso_style_removed_on_top_level_p_only():
    inp = '<p style="mso-font-size: 12pt;">outer</p><p>in <span style="color: red">inner</span></p>'
    out = clean_html_for_paste(inp)
    assert 'style="mso-font-size: 12pt;"' not in out
    assert 'style="color: red"' in out
    assert "inner" in out


def test_empty_input():
    assert clean_html_for_paste("") == ""
    assert clean_html_for_paste("   \n  ") == ""
