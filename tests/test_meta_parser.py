from app.services.meta_parser import extract_meta_from_parsed, meta_variant_list


def test_extract_flat_case_insensitive():
    d = {"TITLE": "T", "Description": "D", "H1": "H"}
    r = extract_meta_from_parsed(d)
    assert r == {"title": "T", "description": "D", "h1": "H"}


def test_extract_results_pascal():
    d = {"results": [{"Title": "RT", "Description": "RD", "H1": "RH"}]}
    r = extract_meta_from_parsed(d)
    assert r["title"] == "RT"
    assert r["description"] == "RD"
    assert r["h1"] == "RH"


def test_extract_variants_key_ci():
    d = {"VARIANTS": [{"title": "vt", "meta_description": "vd"}]}
    r = extract_meta_from_parsed(d)
    assert r["title"] == "vt"
    assert r["description"] == "vd"


def test_extract_nested_response():
    d = {"response": {"Title": "in", "description": "id"}}
    r = extract_meta_from_parsed(d)
    assert r["title"] == "in"
    assert r["description"] == "id"


def test_extract_fallback_other_list_key():
    d = {"options": [{"title": "opt", "description": "od"}]}
    r = extract_meta_from_parsed(d)
    assert r["title"] == "opt"
    assert r["description"] == "od"


def test_meta_variant_list_prefers_results():
    d = {
        "results": [{"a": 1}],
        "variants": [{"b": 2}],
    }
    assert meta_variant_list(d) == [{"a": 1}]


def test_meta_variant_list_variants_when_no_results():
    d = {"Variants": [{"x": 1}]}
    assert meta_variant_list(d) == [{"x": 1}]


def test_extract_empty():
    assert extract_meta_from_parsed({}) == {"title": "", "description": "", "h1": ""}
    assert extract_meta_from_parsed(None) == {"title": "", "description": "", "h1": ""}
