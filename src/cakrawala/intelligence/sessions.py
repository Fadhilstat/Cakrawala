from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MarketSession:
    name: str
    timezone: str
    local_hour: int
    is_open: bool


def _session(name: str, timezone_name: str, start_hour: int, end_hour: int, now: datetime) -> MarketSession:
    local = now.astimezone(ZoneInfo(timezone_name))
    weekday_open = local.weekday() < 5
    if start_hour < end_hour:
        within_hours = start_hour <= local.hour < end_hour
    else:
        within_hours = local.hour >= start_hour or local.hour < end_hour
    return MarketSession(
        name=name,
        timezone=timezone_name,
        local_hour=local.hour,
        is_open=weekday_open and within_hours,
    )


def current_sessions(now: datetime | None = None) -> list[MarketSession]:
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    return [
        _session("Asia", "Asia/Tokyo", 9, 17, reference),
        _session("London", "Europe/London", 8, 17, reference),
        _session("New York", "America/New_York", 8, 17, reference),
    ]
