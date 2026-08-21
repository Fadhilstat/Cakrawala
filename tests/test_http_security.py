from __future__ import annotations

import pytest

from cakrawala.data.http import HttpPolicy, SecurityBoundaryError, _validated_url


def policy() -> HttpPolicy:
    return HttpPolicy(allowed_hosts=frozenset({"example.com"}))


def test_rejects_http() -> None:
    with pytest.raises(SecurityBoundaryError):
        _validated_url("http://example.com/data", policy())


def test_rejects_unlisted_host() -> None:
    with pytest.raises(SecurityBoundaryError):
        _validated_url("https://evil.example/data", policy())


def test_rejects_credentials_in_url() -> None:
    with pytest.raises(SecurityBoundaryError):
        _validated_url("https://user:pass@example.com/data", policy())


def test_accepts_exact_https_host() -> None:
    assert _validated_url("https://example.com/data", policy()) == "https://example.com/data"
