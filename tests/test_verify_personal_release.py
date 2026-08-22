from __future__ import annotations

import json

import pytest
import scripts.verify_personal_release as release


SECURITY_HEADERS = {
    "cache-control": "no-store",
    "x-robots-tag": "noindex, nofollow",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


def _result(
    status: int,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> release.HttpResult:
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    return release.HttpResult(status=status, headers=headers or {}, body=payload)


def test_verify_accepts_secured_anonymous_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(base_url: str, path: str, timeout: float = 15.0) -> release.HttpResult:
        del base_url, timeout
        if path == "/healthz":
            return _result(200, {"service": "cakrawala-dash", "status": "ok"})
        if path == "/releasez":
            return _result(
                200,
                {
                    "service": "cakrawala-personal",
                    "status": "ok",
                    "version": release.__version__,
                },
                SECURITY_HEADERS,
            )
        if path == "/login":
            headers = {
                **SECURITY_HEADERS,
                "content-security-policy": (
                    "default-src 'none'; form-action 'self'; frame-ancestors 'none'"
                ),
            }
            return _result(200, headers=headers)
        return _result(302, headers={**SECURITY_HEADERS, "location": "/login"})

    monkeypatch.setattr(release, "_request", fake_request)
    release.verify("https://example.test")


def test_verify_rejects_public_private_route(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(base_url: str, path: str, timeout: float = 15.0) -> release.HttpResult:
        del base_url, timeout
        if path == "/healthz":
            return _result(200, {"service": "cakrawala-dash", "status": "ok"})
        if path == "/releasez":
            return _result(
                200,
                {
                    "service": "cakrawala-personal",
                    "status": "ok",
                    "version": release.__version__,
                },
                SECURITY_HEADERS,
            )
        if path == "/login":
            headers = {
                **SECURITY_HEADERS,
                "content-security-policy": (
                    "default-src 'none'; form-action 'self'; frame-ancestors 'none'"
                ),
            }
            return _result(200, headers=headers)
        return _result(200, headers=SECURITY_HEADERS)

    monkeypatch.setattr(release, "_request", fake_request)
    with pytest.raises(RuntimeError, match="expected redirect or fail-closed"):
        release.verify("https://example.test")
