from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache:
    """Small process-local cache for public evidence only."""

    def __init__(self, *, max_entries: int = 64) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._entries: dict[str, _Entry[object]] = {}
        self._lock = RLock()

    def get(self, key: str, ttl_seconds: int, loader: Callable[[], T]) -> T:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                return entry.value  # type: ignore[return-value]

        value = loader()
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].expires_at,
                )
                self._entries.pop(oldest_key, None)
            self._entries[key] = _Entry(value=value, expires_at=now + ttl_seconds)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


PUBLIC_CACHE = TTLCache(max_entries=64)
