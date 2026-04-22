from app.services.json_parser import clean_and_parse_json


def test_json_parser_clean():
    raw = '{"key": "value"}'
    res = clean_and_parse_json(raw)
    assert res == {"key": "value"}


def test_json_parser_markdown():
    raw = '```json\n{"test": 123}\n```'
    res = clean_and_parse_json(raw)
    assert res == {"test": 123}


def test_json_parser_with_text():
    raw = 'Here is your json:\n```\n{"a": "b"}\n```\nEnjoy!'
    res = clean_and_parse_json(raw)
    assert res == {"a": "b"}


def test_json_parser_invalid():
    raw = "Just a conversational response without JSON."
    res = clean_and_parse_json(raw)
    assert res == {}


def test_json_parser_meta_flat():
    raw = '{"title": "Best Casino App", "description": "Download now"}'
    res = clean_and_parse_json(raw)
    assert res["title"] == "Best Casino App"


def test_json_parser_meta_results_array():
    raw = '{"results": [{"Title": "Best Casino", "Description": "Download"}]}'
    res = clean_and_parse_json(raw)
    assert res["results"][0]["Title"] == "Best Casino"


def test_json_parser_meta_wrapped():
    raw = '{"response": {"title": "Test", "description": "Desc"}, "confidence": 0.95}'
    res = clean_and_parse_json(raw)
    assert "response" in res


def test_json_parser_with_trailing_text():
    raw = '{"title": "Test"}\n\nHere is your JSON output.'
    res = clean_and_parse_json(raw)
    assert res.get("title") == "Test"


def test_json_parser_unwrap_keys():
    raw = '{"wrapper": {"intent": "transactional", "Taxonomy": "Casino"}}'
    res = clean_and_parse_json(
        raw,
        unwrap_keys={"intent", "Taxonomy", "Attention", "structura"},
    )
    assert res["intent"] == "transactional"


def test_json_parser_no_unwrap_by_default():
    raw = '{"wrapper": {"intent": "transactional"}}'
    res = clean_and_parse_json(raw)
    assert "wrapper" in res
