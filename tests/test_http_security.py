from __future__ import annotations

import pytest

from cakrawala.data.http import HttpPolicy, SecurityBoundaryError, _query_url, _validated_url


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


def test_sensitive_query_value_is_redacted_from_metadata_url() -> None:
    secret = "provider-secret-value"
    url = _query_url(
        "https://example.com/data",
        {"series_id": "TEST", "api_key": secret},
        redact=frozenset({"api_key"}),
    )
    assert secret not in url
    assert "series_id=TEST" in url
    assert "api_key=%5BREDACTED%5D" in url
