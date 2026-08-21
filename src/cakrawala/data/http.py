from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class SecurityBoundaryError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpPolicy:
    allowed_hosts: frozenset[str]
    timeout_seconds: float = 10.0
    max_bytes: int = 4 * 1024 * 1024
    attempts: int = 3
    accepted_content_types: tuple[str, ...] = ("application/json", "text/json")


@dataclass(frozen=True)
class JsonResponse:
    url: str
    status: int
    content_type: str
    payload: Any
    raw: bytes


def _validated_url(url: str, policy: HttpPolicy) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SecurityBoundaryError("Provider URL must use HTTPS")
    if parsed.username or parsed.password:
        raise SecurityBoundaryError("Provider URL must not contain user information")
    host = (parsed.hostname or "").lower()
    if host not in policy.allowed_hosts:
        raise SecurityBoundaryError(f"Host is not allowed: {host}")
    if parsed.port not in (None, 443):
        raise SecurityBoundaryError("Only the standard HTTPS port is allowed")
    return url


def get_json(
    url: str,
    *,
    policy: HttpPolicy,
    params: Mapping[str, str | int | float] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JsonResponse:
    _validated_url(url, policy)
    query = urlencode(params or {}, doseq=False)
    request_url = f"{url}?{query}" if query else url
    request_headers = {"User-Agent": "Cakrawala/0.1 public-research-client"}
    request_headers.update(headers or {})

    last_error: Exception | None = None
    for attempt in range(policy.attempts):
        try:
            request = Request(request_url, headers=request_headers, method="GET")
            with urlopen(request, timeout=policy.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                content_type = response.headers.get_content_type().lower()
                if content_type not in policy.accepted_content_types:
                    raise ProviderRequestError(f"Unexpected content type: {content_type}")
                raw = response.read(policy.max_bytes + 1)
                if len(raw) > policy.max_bytes:
                    raise ProviderRequestError("Provider response exceeded the configured size limit")
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ProviderRequestError("Provider returned invalid UTF-8 JSON") from exc
                return JsonResponse(
                    url=request_url,
                    status=status,
                    content_type=content_type,
                    payload=payload,
                    raw=raw,
                )
        except HTTPError as exc:
            last_error = exc
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt + 1 >= policy.attempts:
                break
        except URLError as exc:
            last_error = exc
            if attempt + 1 >= policy.attempts:
                break
        if attempt + 1 < policy.attempts:
            time.sleep(min(2**attempt, 4))

    raise ProviderRequestError("Provider request failed after bounded retries") from last_error
