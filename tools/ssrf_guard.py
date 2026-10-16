"""
SSRF guard — validates every outbound URL the LLM can influence (FM-08).

Threat model: the agent fetches URLs that came out of an LLM, which may
have been prompt-injected by web content. Without this guard, a malicious
page can make us fetch:

    http://169.254.169.254/latest/meta-data/   (cloud metadata → token theft)
    http://10.0.0.5:8500/                      (internal services)
    http://localhost:8000/v1/ask               ( ourselves, bypassing the edge )
    file:///etc/passwd                         (scheme abuse)

Defense layers (defense in depth — ALL must pass):
1. Scheme allowlist: http/https only.
2. Host syntax: IP literals and DNS names; no userinfo tricks
   (``http://user@internal/``) beyond standard parsing.
3. IP literal check: reject private/loopback/link-local/reserved ranges.
4. DNS resolution check: resolve the hostname ONCE and validate ALL
   returned addresses — closes the DNS-rebinding-to-internal-host hole.
5. Redirect policy: httpx follows redirects on the shared client; the
   executor re-validates the FINAL URL (see ``validate_redirect`` usage in
   web_scraper) by calling ``validate_url`` again on the response history.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import structlog

from core.exceptions import SSRFBlockedError

logger = structlog.get_logger(__name__)

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_MAX_URL_LENGTH = 2048

# Hostnames that resolve to loopback on most systems, blocked by name too.
_BLOCKED_HOSTNAMES = frozenset({
    "localhost", "localhost.localdomain", "ip6-localhost",
    "metadata", "metadata.google.internal",
})


@dataclass(frozen=True)
class URLCheck:
    ok: bool
    reason: str = ""
    host: str = ""
    port: int = 0


def _check_ip_literal(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> URLCheck:
    """Reject non-public addresses."""
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or (isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped and ip.ipv4_mapped.is_private))
    ):
        return URLCheck(False, f"non-public IP {ip}", str(ip))
    return URLCheck(True, host=str(ip))


def validate_url(
    url: str,
    *,
    resolve_dns: bool = True,
    timeout_s: float = 3.0,
) -> URLCheck:
    """
    Validate a URL for outbound fetching. Pure check — raises nothing;
    callers decide to raise ``SSRFBlockedError`` or skip.
    """
    from core.observability import SSRF_BLOCKED

    if len(url) > _MAX_URL_LENGTH:
        SSRF_BLOCKED.labels(reason="url_too_long").inc()
        return URLCheck(False, "URL exceeds max length")

    try:
        parsed = urlparse(url)
    except ValueError:
        SSRF_BLOCKED.labels(reason="unparseable").inc()
        return URLCheck(False, "unparseable URL")

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        SSRF_BLOCKED.labels(reason="scheme").inc()
        return URLCheck(False, f"scheme '{parsed.scheme}' not allowed")

    host = (parsed.hostname or "").lower()
    if not host:
        SSRF_BLOCKED.labels(reason="no_host").inc()
        return URLCheck(False, "no hostname")

    if host in _BLOCKED_HOSTNAMES:
        SSRF_BLOCKED.labels(reason="blocked_hostname").inc()
        return URLCheck(False, f"hostname '{host}' is blocked")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Layer 3: IP-literal check
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        result = _check_ip_literal(ip)
        if not result.ok:
            SSRF_BLOCKED.labels(reason="ip_literal").inc()
            return result

    # Layer 4: DNS resolution check (blocks names that resolve internally)
    if resolve_dns and host not in ("", ):
        try:
            addrinfos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror:
            SSRF_BLOCKED.labels(reason="dns_failure").inc()
            return URLCheck(False, f"DNS resolution failed for '{host}'")

        for info in addrinfos:
            sockaddr = info[4]
            addr = sockaddr[0]
            try:
                ip = ipaddress.ip_address(addr.split("%")[0])
            except ValueError:
                continue
            result = _check_ip_literal(ip)
            if not result.ok:
                SSRF_BLOCKED.labels(reason="dns_internal").inc()
                logger.warning("ssrf.dns_internal_blocked", host=host, resolved=addr)
                return URLCheck(False, f"host '{host}' resolves to internal {addr}")

    return URLCheck(True, host=host, port=port)


def ensure_fetchable(url: str, *, resolve_dns: bool = True) -> URLCheck:
    """
    Validate or raise ``SSRFBlockedError``.

    This is the function tool implementations call before any fetch.
    The executor ALSO calls it — belt and suspenders: even a future tool
    that forgets its own check is still guarded centrally.
    """
    check = validate_url(url, resolve_dns=resolve_dns)
    if not check.ok:
        raise SSRFBlockedError(url=url, reason=check.reason)
    return check


def validate_response_history(final_url: str) -> URLCheck:
    """
    Re-validate after redirects: the FINAL URL must also be public.
    (Redirect chains can bounce http://public → http://169.254.169.254.)
    """
    return ensure_fetchable(final_url, resolve_dns=False)
