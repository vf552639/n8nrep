import pytest

from app.utils.url_safety import UnsafeUrlError, raise_if_url_unsafe_for_ssrf


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/foo",
        "http://localhost/foo",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/",
        "file:///etc/passwd",
        "ftp://example.com/",
    ],
)
def test_raise_if_url_unsafe_for_ssrf_blocks(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        raise_if_url_unsafe_for_ssrf(url)


def test_raise_if_url_unsafe_for_ssrf_blocks_nonstandard_port() -> None:
    with pytest.raises(UnsafeUrlError):
        raise_if_url_unsafe_for_ssrf("http://example.com:8080/")


def test_raise_if_url_unsafe_for_ssrf_allows_public_https() -> None:
    raise_if_url_unsafe_for_ssrf("https://example.com/")
