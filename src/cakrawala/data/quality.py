from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    errors: tuple[str, ...]


def require_mapping(payload: Any, required_keys: Iterable[str]) -> QualityResult:
    if not isinstance(payload, dict):
        return QualityResult(False, ("payload_not_mapping",))
    missing = tuple(sorted(key for key in required_keys if key not in payload))
    return QualityResult(not missing, tuple(f"missing_key:{key}" for key in missing))


def require_sequence(payload: Any, minimum_items: int = 1) -> QualityResult:
    if not isinstance(payload, list):
        return QualityResult(False, ("payload_not_sequence",))
    if len(payload) < minimum_items:
        return QualityResult(False, ("sequence_too_short",))
    return QualityResult(True, ())
