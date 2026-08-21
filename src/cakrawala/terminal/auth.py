from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class OwnerPolicy:
    issuer: str
    audience: str
    subject: str


def authorize_verified_claims(claims: Mapping[str, Any], policy: OwnerPolicy) -> bool:
    """Authorize claims only after an OIDC library has verified token signature and expiry."""
    return (
        claims.get("iss") == policy.issuer
        and claims.get("aud") == policy.audience
        and claims.get("sub") == policy.subject
    )
