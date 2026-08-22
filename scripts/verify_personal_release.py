from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cakrawala import __version__


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _request(base_url: str, path: str, timeout: float = 15.0) -> HttpResult:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(
        url,
        headers={"User-Agent": "CakrawalaReleaseVerifier/1.0"},
        method="GET",
    )
    opener = build_opener(_NoRedirect())
    try:
        response = opener.open(request, timeout=timeout)
        body = response.read(262_145)
        if len(body) > 262_144:
            raise RuntimeError(f"Response too large for {path}")
        return HttpResult(
            status=int(response.status),
            headers={key.lower(): value for key, value in response.headers.items()},
            body=body,
        )
    except HTTPError as exc:
        body = exc.read(262_145)
        if len(body) > 262_144:
            raise RuntimeError(f"Response too large for {path}") from exc
        return HttpResult(
            status=int(exc.code),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=body,
        )
    except URLError as exc:
        raise RuntimeError(f"Unable to reach {url}: {exc.reason}") from exc


def _require_security_headers(result: HttpResult, path: str) -> None:
    expected = {
        "cache-control": "no-store",
        "x-robots-tag": "noindex, nofollow",
        "referrer-policy": "no-referrer",
        "x-frame-options": "DENY",
    }
    for name, value in expected.items():
        actual = result.headers.get(name, "")
        if value.lower() not in actual.lower():
            raise RuntimeError(
                f"Missing or unexpected {name} on {path}: {actual or 'missing'}"
            )
    permissions = result.headers.get("permissions-policy", "")
    for directive in ("camera=()", "microphone=()", "geolocation=()", "payment=()"):
        if directive not in permissions:
            raise RuntimeError(f"Missing permissions policy directive on {path}: {directive}")


def _verify_health(base_url: str) -> None:
    result = _request(base_url, "/healthz")
    if result.status != 200:
        raise RuntimeError(f"/healthz returned HTTP {result.status}")
    payload = json.loads(result.body.decode("utf-8"))
    if payload.get("status") != "ok":
        raise RuntimeError("/healthz did not report status=ok")


def _verify_release(base_url: str) -> None:
    result = _request(base_url, "/releasez")
    if result.status != 200:
        raise RuntimeError(f"/releasez returned HTTP {result.status}")
    _require_security_headers(result, "/releasez")
    payload = json.loads(result.body.decode("utf-8"))
    expected = {
        "service": "cakrawala-personal",
        "status": "ok",
        "version": __version__,
    }
    if payload != expected:
        raise RuntimeError(f"Unexpected /releasez payload: {payload}")


def _verify_login_boundary(base_url: str) -> None:
    login = _request(base_url, "/login")
    if login.status not in {200, 503}:
        raise RuntimeError(f"/login returned unsafe or unexpected HTTP {login.status}")
    _require_security_headers(login, "/login")
    if login.status == 200:
        csp = login.headers.get("content-security-policy", "")
        for directive in ("default-src 'none'", "form-action 'self'", "frame-ancestors 'none'"):
            if directive not in csp:
                raise RuntimeError(f"Missing login CSP directive: {directive}")

    for path in (
        "/",
        "/personal/forex",
        "/personal/forex/review",
        "/personal/forex/risk",
        "/personal/forex/system",
        "/personal/market",
        "/personal/ai-lab",
    ):
        result = _request(base_url, path)
        _require_security_headers(result, path)
        if result.status == 302:
            location = result.headers.get("location", "")
            if not location.endswith("/login"):
                raise RuntimeError(f"Anonymous {path} redirected somewhere other than /login")
        elif result.status != 503:
            raise RuntimeError(
                f"Anonymous {path} returned HTTP {result.status}; expected redirect or fail-closed"
            )


def verify(base_url: str) -> None:
    _verify_health(base_url)
    _verify_release(base_url)
    _verify_login_boundary(base_url)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the deployed Cakrawala Personal Mode release boundary."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--deployment-url")
    args = parser.parse_args()

    targets = []
    if args.deployment_url:
        targets.append(("deployment", args.deployment_url))
    targets.append(("canonical", args.base_url))

    try:
        for label, target in targets:
            verify(target)
            print(f"{label} release verification passed")
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"release verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
