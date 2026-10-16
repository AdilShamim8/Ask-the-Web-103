"""
SSRF guard tests — the regression suite for FMEA FM-08.

Every test case here is an attack that a prompt-injected LLM can
realistically produce. If one of these starts failing, treat it as a
SEC-1 regression, not a test flake.
"""

from __future__ import annotations

import pytest

from core.exceptions import SSRFBlockedError
from tools.ssrf_guard import URLCheck, ensure_fetchable, validate_url


class TestSchemeValidation:
    def test_http_allowed(self) -> None:
        assert validate_url("http://example.com", resolve_dns=False).ok

    def test_https_allowed(self) -> None:
        assert validate_url("https://example.com", resolve_dns=False).ok

    def test_file_blocked(self) -> None:
        check = validate_url("file:///etc/passwd", resolve_dns=False)
        assert not check.ok
        assert "scheme" in check.reason

    def test_ftp_blocked(self) -> None:
        assert not validate_url("ftp://example.com", resolve_dns=False).ok

    def test_javascript_blocked(self) -> None:
        assert not validate_url("javascript:alert(1)", resolve_dns=False).ok

    def test_url_length_cap(self) -> None:
        long_url = "https://example.com/" + "a" * 3000
        check = validate_url(long_url, resolve_dns=False)
        assert not check.ok
        assert "length" in check.reason


class TestPrivateNetworkBlocking:
    """Cloud metadata + internal ranges must be unreachable."""

    @pytest.mark.parametrize("url", [
        "http://169.254.169.254/latest/meta-data/",   # AWS/GCP metadata
        "http://metadata.google.internal/",            # GCP by name
        "http://10.0.0.5:8500/",                       # private class A
        "http://172.16.1.1/admin",                     # private class B
        "http://192.168.1.1/router",                   # private class C
        "http://127.0.0.1:8000/v1/ask",                # loopback (us!)
        "http://localhost:8000/v1/ask",                # loopback by name
        "http://0.0.0.0/",                             # unspecified
        "http://[::1]:8080/",                          # IPv6 loopback
    ])
    def test_internal_targets_blocked(self, url: str) -> None:
        check = validate_url(url, resolve_dns=False)
        assert not check.ok, f"{url} must be blocked"

    def test_public_ip_allowed(self) -> None:
        assert validate_url("http://8.8.8.8/", resolve_dns=False).ok

    def test_ensure_fetchable_raises(self) -> None:
        with pytest.raises(SSRFBlockedError):
            ensure_fetchable("http://169.254.169.254/", resolve_dns=False)

    def test_ensure_fetchable_passes_public(self) -> None:
        check = ensure_fetchable("https://example.com", resolve_dns=False)
        assert check.ok


class TestValidationShape:
    def test_check_carries_host(self) -> None:
        check = validate_url("https://example.com/path", resolve_dns=False)
        assert isinstance(check, URLCheck)
        assert check.host == "example.com"

    def test_no_host_rejected(self) -> None:
        assert not validate_url("https://", resolve_dns=False).ok

    def test_unparseable_rejected(self) -> None:
        assert not validate_url("http://[::invalid", resolve_dns=False).ok
