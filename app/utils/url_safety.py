"""Guard against SSRF when the server fetches user-supplied URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    """Raised when a URL must not be fetched from the backend."""


def raise_if_url_unsafe_for_ssrf(url: str) -> None:
    """
    Resolve hostname and reject loopback, RFC1918, link-local, multicast, etc.
    Only http/https; hostname required; ports 80 and 443 only.
    """
    raw = (url or "").strip()
    if not raw:
        raise UnsafeUrlError("URL is empty")

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsafeUrlError("Only http and https URLs are allowed")

    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL must include a hostname")

    h = host.lower()
    if h in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or h.endswith(".localhost"):
        raise UnsafeUrlError("Disallowed hostname")

    port = parsed.port
    if port is not None and port not in (80, 443):
        raise UnsafeUrlError("Only default ports or explicit 80/443 are allowed")

    try:
        port_for_lookup = port or (443 if scheme == "https" else 80)
        infos = socket.getaddrinfo(host, port_for_lookup, type=socket.SOCK_STREAM)
    except OSError as e:
        raise UnsafeUrlError(f"Could not resolve host: {e}") from e

    if not infos:
        raise UnsafeUrlError("No addresses resolved for host")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        ):
            raise UnsafeUrlError(f"Disallowed target address: {ip_str}")


def safe_requests_get_bytes(
    url: str,
    *,
    timeout: tuple[float, float] = (3.0, 10.0),
    max_bytes: int = 8 * 1024 * 1024,
    allowed_content_prefixes: tuple[str, ...] = ("image/",),
) -> bytes:
    """HTTP GET with SSRF checks, size cap, and optional Content-Type filter."""
    import requests

    raise_if_url_unsafe_for_ssrf(url)
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if allowed_content_prefixes and not ct.startswith(allowed_content_prefixes):
            raise ValueError(f"Unexpected content type: {ct or 'missing'}")
        out = bytearray()
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            out.extend(chunk)
            if len(out) > max_bytes:
                raise ValueError("Response exceeds maximum size")
    return bytes(out)
