import pytest
from app.services.json_parser import clean_and_parse_json

def test_json_parser_clean():
    # Test valid json
    raw = '{"key": "value"}'
    res = clean_and_parse_json(raw)
    assert res == {"key": "value"}

def test_json_parser_markdown():
    # Test markdown fenced json
    raw = "```json\n{\"test\": 123}\n```"
    res = clean_and_parse_json(raw)
    assert res == {"test": 123}

def test_json_parser_with_text():
    # Test text before and after json
    raw = 'Here is your json:\n```\n{"a": "b"}\n```\nEnjoy!'
    res = clean_and_parse_json(raw)
    assert res == {"a": "b"}

def test_json_parser_invalid():
    # Test fallback on completely invalid json
    raw = "Just a conversational response without JSON."
    res = clean_and_parse_json(raw)
    # The parser returns the empty dict if loading fails completely to avoid breaking pipeline
    assert res == {}
