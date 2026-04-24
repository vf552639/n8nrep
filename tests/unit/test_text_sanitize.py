from app.services.scraper import parse_html
from app.utils.text_sanitize import strip_nul


def test_strip_nul_string():
    assert strip_nul("a\x00b") == "ab"
    assert strip_nul("") == ""


def test_strip_nul_nested():
    assert strip_nul({"a": "x\x00y", "b": [1, "z\x00"]}) == {"a": "xy", "b": [1, "z"]}


def test_parse_html_strips_nul():
    html = "<html><head><title>T\x00T</title></head><body><p>ab\x00c</p></body></html>"
    out = parse_html(html)
    assert "\x00" not in out["text"]
    assert "\x00" not in out["meta_title"]
    assert "\x00" not in "".join(out["headers"]["h1"])
