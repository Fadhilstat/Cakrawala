from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from math import isfinite
from typing import Protocol


class DailyPricePoint(Protocol):
    observed_at: datetime
    close: float


class MarketBias(StrEnum):
    BUY_BIAS = "BUY BIAS"
    SELL_BIAS = "SELL BIAS"
    WAIT = "WAIT"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class MarketAssessment:
    symbol: str
    bias: MarketBias
    as_of: date | None
    change_1d_pct: float | None
    change_5d_pct: float | None
    change_20d_pct: float | None
    rationale: tuple[str, ...]
    invalidation: str


def _change(closes: list[float], periods: int) -> float | None:
    if len(closes) <= periods:
        return None
    previous = closes[-1 - periods]
    latest = closes[-1]
    if previous <= 0:
        return None
    return ((latest / previous) - 1.0) * 100


def _direction(value: float | None, deadband_pct: float) -> int:
    if value is None or abs(value) < deadband_pct:
        return 0
    return 1 if value > 0 else -1


def assess_change_windows(
    symbol: str,
    *,
    as_of: date,
    change_1d_pct: float | None,
    change_5d_pct: float | None,
    change_20d_pct: float | None,
    today: date | None = None,
    maximum_age_days: int = 5,
    deadband_pct: float = 0.05,
) -> MarketAssessment:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol is required")
    if maximum_age_days < 1:
        raise ValueError("maximum_age_days must be positive")
    if deadband_pct < 0:
        raise ValueError("deadband_pct must not be negative")

    reference_day = today or datetime.now(UTC).date()
    if as_of > reference_day:
        return MarketAssessment(
            symbol=normalized_symbol,
            bias=MarketBias.INSUFFICIENT,
            as_of=as_of,
            change_1d_pct=None,
            change_5d_pct=None,
            change_20d_pct=None,
            rationale=("The newest observation is future-dated and cannot be used.",),
            invalidation="Wait for a valid completed observation from the data provider.",
        )

    age_days = (reference_day - as_of).days
    if age_days > maximum_age_days:
        return MarketAssessment(
            symbol=normalized_symbol,
            bias=MarketBias.INSUFFICIENT,
            as_of=as_of,
            change_1d_pct=None,
            change_5d_pct=None,
            change_20d_pct=None,
            rationale=(f"The newest completed observation is {age_days} days old.",),
            invalidation="Refresh the source before using this assessment.",
        )

    changes = (change_1d_pct, change_5d_pct, change_20d_pct)
    if any(value is None or not isfinite(float(value)) for value in changes):
        return MarketAssessment(
            symbol=normalized_symbol,
            bias=MarketBias.INSUFFICIENT,
            as_of=as_of,
            change_1d_pct=change_1d_pct,
            change_5d_pct=change_5d_pct,
            change_20d_pct=change_20d_pct,
            rationale=("All 1D, 5D, and 20D completed-price windows are required.",),
            invalidation="Wait until the source provides enough completed history.",
        )

    directions = tuple(_direction(value, deadband_pct) for value in changes)
    if directions == (1, 1, 1):
        bias = MarketBias.BUY_BIAS
        rationale = (
            "Completed daily price momentum is positive across 1D, 5D, and 20D windows.",
            "The assessment is momentum context, not an execution instruction.",
        )
        invalidation = "Bias weakens if the 1D or 5D completed-price direction turns non-positive."
    elif directions == (-1, -1, -1):
        bias = MarketBias.SELL_BIAS
        rationale = (
            "Completed daily price momentum is negative across 1D, 5D, and 20D windows.",
            "The assessment is momentum context, not an execution instruction.",
        )
        invalidation = "Bias weakens if the 1D or 5D completed-price direction turns non-negative."
    else:
        bias = MarketBias.WAIT
        rationale = (
            "Completed daily price windows are mixed or too close to the neutral deadband.",
            "Waiting avoids forcing a directional view when horizons disagree.",
        )
        invalidation = "Reassess after the directional windows become aligned on completed data."

    return MarketAssessment(
        symbol=normalized_symbol,
        bias=bias,
        as_of=as_of,
        change_1d_pct=change_1d_pct,
        change_5d_pct=change_5d_pct,
        change_20d_pct=change_20d_pct,
        rationale=rationale,
        invalidation=invalidation,
    )


def apply_fx_context_gates(
    assessment: MarketAssessment,
    *,
    event_calendar_available: bool,
    event_risk: bool,
    macro_alignment: str,
) -> MarketAssessment:
    normalized_macro = macro_alignment.strip().upper()
    allowed_macro = {"SUPPORTS_UP", "SUPPORTS_DOWN", "MIXED", "NO_CONTEXT"}
    if normalized_macro not in allowed_macro:
        raise ValueError("macro_alignment is not supported")

    if assessment.bias == MarketBias.INSUFFICIENT:
        return assessment

    if not event_calendar_available:
        return MarketAssessment(
            symbol=assessment.symbol,
            bias=MarketBias.INSUFFICIENT,
            as_of=assessment.as_of,
            change_1d_pct=assessment.change_1d_pct,
            change_5d_pct=assessment.change_5d_pct,
            change_20d_pct=assessment.change_20d_pct,
            rationale=assessment.rationale
            + ("Official scheduled-event risk could not be verified.",),
            invalidation="Refresh the official event calendar before using the FX bias.",
        )

    if event_risk:
        return MarketAssessment(
            symbol=assessment.symbol,
            bias=MarketBias.WAIT,
            as_of=assessment.as_of,
            change_1d_pct=assessment.change_1d_pct,
            change_5d_pct=assessment.change_5d_pct,
            change_20d_pct=assessment.change_20d_pct,
            rationale=assessment.rationale
            + ("A scheduled high-impact release is close enough to raise event risk.",),
            invalidation="Reassess after the event is released and completed-price data refreshes.",
        )

    trend_up = assessment.bias == MarketBias.BUY_BIAS
    trend_down = assessment.bias == MarketBias.SELL_BIAS
    macro_conflict = (
        (trend_up and normalized_macro == "SUPPORTS_DOWN")
        or (trend_down and normalized_macro == "SUPPORTS_UP")
    )
    if macro_conflict:
        return MarketAssessment(
            symbol=assessment.symbol,
            bias=MarketBias.WAIT,
            as_of=assessment.as_of,
            change_1d_pct=assessment.change_1d_pct,
            change_5d_pct=assessment.change_5d_pct,
            change_20d_pct=assessment.change_20d_pct,
            rationale=assessment.rationale
            + ("Recent macro surprise evidence conflicts with the price direction.",),
            invalidation="Wait for price and macro evidence to stop materially conflicting.",
        )

    if normalized_macro == "MIXED":
        return MarketAssessment(
            symbol=assessment.symbol,
            bias=assessment.bias,
            as_of=assessment.as_of,
            change_1d_pct=assessment.change_1d_pct,
            change_5d_pct=assessment.change_5d_pct,
            change_20d_pct=assessment.change_20d_pct,
            rationale=assessment.rationale
            + ("Recent macro surprise evidence is mixed and does not confirm the bias.",),
            invalidation=assessment.invalidation,
        )

    macro_support = (
        (trend_up and normalized_macro == "SUPPORTS_UP")
        or (trend_down and normalized_macro == "SUPPORTS_DOWN")
    )
    if macro_support:
        rationale = assessment.rationale + (
            "Recent macro surprise evidence supports the completed-price direction.",
        )
    else:
        rationale = assessment.rationale + (
            "No fresh macro surprise context is available to confirm or veto the bias.",
        )

    return MarketAssessment(
        symbol=assessment.symbol,
        bias=assessment.bias,
        as_of=assessment.as_of,
        change_1d_pct=assessment.change_1d_pct,
        change_5d_pct=assessment.change_5d_pct,
        change_20d_pct=assessment.change_20d_pct,
        rationale=rationale,
        invalidation=assessment.invalidation,
    )


def assess_daily_prices(
    symbol: str,
    points: list[DailyPricePoint],
    *,
    today: date | None = None,
    maximum_age_days: int = 5,
    deadband_pct: float = 0.05,
) -> MarketAssessment:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol is required")

    ordered = sorted(points, key=lambda item: item.observed_at)
    unique: dict[datetime, DailyPricePoint] = {}
    for point in ordered:
        close = float(point.close)
        if not isfinite(close) or close <= 0:
            raise ValueError("daily close values must be finite and positive")
        unique[point.observed_at] = point
    ordered = list(unique.values())

    if len(ordered) < 21:
        return MarketAssessment(
            symbol=normalized_symbol,
            bias=MarketBias.INSUFFICIENT,
            as_of=ordered[-1].observed_at.date() if ordered else None,
            change_1d_pct=None,
            change_5d_pct=None,
            change_20d_pct=None,
            rationale=("At least 21 completed daily observations are required.",),
            invalidation="Collect enough completed daily observations before assigning a bias.",
        )

    closes = [float(point.close) for point in ordered]
    return assess_change_windows(
        normalized_symbol,
        as_of=ordered[-1].observed_at.date(),
        change_1d_pct=_change(closes, 1),
        change_5d_pct=_change(closes, 5),
        change_20d_pct=_change(closes, 20),
        today=today,
        maximum_age_days=maximum_age_days,
        deadband_pct=deadband_pct,
    )
