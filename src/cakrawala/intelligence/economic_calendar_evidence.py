from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cakrawala.intelligence.economic_surprise import (
    EconomicRelease,
    EconomicSurpriseAssessment,
    assess_economic_release,
)

SNAPSHOT_PATH = Path("data/economic_calendar/latest.json")
MAX_EVENTS = 16
_ALLOWED_IMPORTANCE = {"high", "medium"}
_ALLOWED_MACRO_ALIGNMENT = {
    "SUPPORTS_UP",
    "SUPPORTS_DOWN",
    "MIXED",
    "NO_CONTEXT",
}
_IMPULSE_SCORE = {
    "HAWKISH_PRESSURE": 1.0,
    "DOVISH_PRESSURE": -1.0,
    "GROWTH_POSITIVE": 0.5,
    "GROWTH_NEGATIVE": -0.5,
    "NEUTRAL": 0.0,
}


@dataclass(frozen=True)
class CalendarEventEvidence:
    event: str
    currency: str
    released_at: datetime
    importance: str
    actual: str | float | int | None
    forecast: str | float | int | None
    previous: str | float | int | None
    consensus_source: str
    consensus_url: str
    official_source: str | None
    official_url: str | None
    actual_verified: bool
    assessment: EconomicSurpriseAssessment


@dataclass(frozen=True)
class EconomicCalendarSnapshot:
    generated_at: datetime
    as_of: str
    events: tuple[CalendarEventEvidence, ...]

    def is_fresh(self, *, max_age_hours: int = 36) -> bool:
        return datetime.now(UTC) - self.generated_at <= timedelta(hours=max_age_hours)


@dataclass(frozen=True)
class PairMacroContext:
    pair: str
    alignment: str
    score: float
    base_score: float
    quote_score: float
    relevant_events: int
    verified_events: int
    reasons: tuple[str, ...]


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone information")
    return parsed.astimezone(UTC)


def _https_url(value: Any, field: str, *, required: bool) -> str | None:
    if value in {None, ""}:
        if required:
            raise ValueError(f"{field} is required")
        return None
    text = str(value).strip()
    if not text.startswith("https://"):
        raise ValueError(f"{field} must use HTTPS")
    return text


def _parse_event(item: Any) -> CalendarEventEvidence:
    if not isinstance(item, dict):
        raise ValueError("calendar event must be an object")

    event = " ".join(str(item.get("event", "")).split())
    currency = str(item.get("currency", "")).strip().upper()
    importance = str(item.get("importance", "high")).strip().lower()
    consensus_source = str(item.get("consensus_source", "")).strip()
    official_source_raw = str(item.get("official_source", "")).strip()
    actual_verified = item.get("actual_verified") is True

    if not event:
        raise ValueError("calendar event name is required")
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("calendar event currency must be a three-letter code")
    if importance not in _ALLOWED_IMPORTANCE:
        raise ValueError("calendar event importance must be high or medium")
    if not consensus_source:
        raise ValueError("consensus_source is required")

    consensus_url = _https_url(item.get("consensus_url"), "consensus_url", required=True)
    official_url = _https_url(item.get("official_url"), "official_url", required=False)
    official_source = official_source_raw or None
    if actual_verified and (official_source is None or official_url is None):
        raise ValueError("verified actual values require an official source and URL")

    release = EconomicRelease(
        event=event,
        currency=currency,
        actual=item.get("actual"),
        forecast=item.get("forecast"),
        previous=item.get("previous"),
        source=consensus_source,
        source_url=consensus_url or "",
    )
    assessment = assess_economic_release(release)
    if assessment.actual is None:
        raise ValueError("calendar event actual value must be usable")

    return CalendarEventEvidence(
        event=event,
        currency=currency,
        released_at=_parse_datetime(item.get("released_at"), "released_at"),
        importance=importance,
        actual=item.get("actual"),
        forecast=item.get("forecast"),
        previous=item.get("previous"),
        consensus_source=consensus_source,
        consensus_url=consensus_url or "",
        official_source=official_source,
        official_url=official_url,
        actual_verified=actual_verified,
        assessment=assessment,
    )


def parse_calendar_snapshot(payload: Any) -> EconomicCalendarSnapshot:
    if not isinstance(payload, dict):
        raise ValueError("economic calendar snapshot must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported economic calendar schema version")

    events_raw = payload.get("events")
    if not isinstance(events_raw, list):
        raise ValueError("events must be a list")
    if len(events_raw) > MAX_EVENTS:
        raise ValueError(f"economic calendar snapshot is limited to {MAX_EVENTS} events")

    events = tuple(sorted((_parse_event(item) for item in events_raw), key=lambda item: item.released_at, reverse=True))
    return EconomicCalendarSnapshot(
        generated_at=_parse_datetime(payload.get("generated_at"), "generated_at"),
        as_of=str(payload.get("as_of", "")).strip(),
        events=events,
    )


def load_calendar_snapshot(path: Path = SNAPSHOT_PATH) -> EconomicCalendarSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_calendar_snapshot(payload)


def _event_weight(event: CalendarEventEvidence, now: datetime) -> float:
    age = now - event.released_at
    if age < timedelta(0):
        return 0.0
    if age <= timedelta(days=7):
        recency = 1.0
    elif age <= timedelta(days=14):
        recency = 0.75
    elif age <= timedelta(days=21):
        recency = 0.5
    else:
        return 0.0
    verification = 1.0 if event.actual_verified else 0.5
    return recency * verification


def _currency_score(
    currency: str,
    events: tuple[CalendarEventEvidence, ...],
    now: datetime,
) -> tuple[float, int, int]:
    weighted = 0.0
    total_weight = 0.0
    count = 0
    verified = 0
    for event in events:
        if event.currency != currency:
            continue
        impulse = _IMPULSE_SCORE.get(event.assessment.policy_impulse)
        if impulse is None:
            continue
        weight = _event_weight(event, now)
        if weight <= 0:
            continue
        weighted += impulse * weight
        total_weight += weight
        count += 1
        if event.actual_verified:
            verified += 1
    if total_weight == 0:
        return 0.0, count, verified
    return weighted / total_weight, count, verified


def macro_context_for_pair(
    pair: str,
    snapshot: EconomicCalendarSnapshot,
    *,
    now: datetime | None = None,
) -> PairMacroContext:
    normalized = pair.strip().upper().replace("/", "")
    if len(normalized) != 6 or not normalized.isalpha():
        raise ValueError("pair must contain two three-letter currency codes")

    reference = (now or datetime.now(UTC)).astimezone(UTC)
    base = normalized[:3]
    quote = normalized[3:]
    base_score, base_count, base_verified = _currency_score(base, snapshot.events, reference)
    quote_score, quote_count, quote_verified = _currency_score(quote, snapshot.events, reference)
    relevant = base_count + quote_count
    verified = base_verified + quote_verified

    if relevant == 0:
        alignment = "NO_CONTEXT"
        score = 0.0
        reasons = ("No recent scored macro surprise evidence is available for this pair.",)
    else:
        score = max(-1.0, min(1.0, base_score - quote_score))
        if score >= 0.25:
            alignment = "SUPPORTS_UP"
        elif score <= -0.25:
            alignment = "SUPPORTS_DOWN"
        else:
            alignment = "MIXED"
        reasons = (
            f"Recent macro evidence covers {relevant} scored releases for {base} and {quote}.",
            f"{verified} of those releases have an official actual-value cross-check.",
            "Macro context may confirm or veto price-trend evidence, but it cannot create a trade signal by itself.",
        )

    if alignment not in _ALLOWED_MACRO_ALIGNMENT:
        raise RuntimeError("unexpected macro alignment")

    return PairMacroContext(
        pair=normalized,
        alignment=alignment,
        score=score,
        base_score=base_score,
        quote_score=quote_score,
        relevant_events=relevant,
        verified_events=verified,
        reasons=reasons,
    )
