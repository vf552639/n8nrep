"""Tests for programmatic_html_insert."""

from app.services.html_inserter import programmatic_html_insert


def test_placeholder_content():
    tpl = "<html><body><div>{{content}}</div></body></html>"
    article = "<p>Hello world</p>"
    out = programmatic_html_insert(tpl, article)
    assert "{{content}}" not in out
    assert "Hello world" in out


def test_main_container():
    tpl = "<html><body><main><p>old</p></main></body></html>"
    article = "<section><h2>T</h2><p>x</p></section>"
    out = programmatic_html_insert(tpl, article)
    assert "old" not in out
    assert "T" in out and "x" in out


def test_empty_template_returns_article():
    assert programmatic_html_insert("", "<p>a</p>") == "<p>a</p>"
    assert programmatic_html_insert("   ", "<p>b</p>") == "<p>b</p>"


def test_no_container_returns_article():
    tpl = "<html><body><span>x</span></body></html>"
    article = "<p>only</p>"
    out = programmatic_html_insert(tpl, article)
    assert out == article
