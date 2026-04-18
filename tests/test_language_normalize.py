from app.utils.language_normalize import normalize_language


def test_normalize_language_basic():
    assert normalize_language("french") == "French"
    assert normalize_language("  ENGLISH  ") == "English"
    assert normalize_language("GERMAN") == "German"


def test_normalize_language_multi_word():
    assert normalize_language("brazilian portuguese") == "Brazilian Portuguese"


def test_normalize_language_empty():
    assert normalize_language("") == ""
    assert normalize_language("   ") == ""
    assert normalize_language(None) is None
