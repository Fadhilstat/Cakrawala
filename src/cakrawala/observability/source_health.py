from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    checked_at: datetime
    detail: str


def run_check(name: str, check: Callable[[], object]) -> HealthCheck:
    checked_at = datetime.now(UTC)
    try:
        check()
    except Exception as exc:
        return HealthCheck(name, "failed", checked_at, type(exc).__name__)
    return HealthCheck(name, "healthy", checked_at, "ok")
