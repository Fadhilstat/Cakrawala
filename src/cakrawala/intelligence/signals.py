from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class Signal(StrEnum):
    BUY = "BUY"
    HOLD = "HOLD"
    AVOID = "AVOID"
    NO_SIGNAL = "NO SIGNAL"


@dataclass(frozen=True)
class SignalInputs:
    direction_probability: float | None
    forecast_volatility: float | None
    model_health: float | None
    prediction_generated_at: datetime | None


@dataclass(frozen=True)
class SignalPolicy:
    buy_probability_min: float = 0.62
    avoid_probability_max: float = 0.42
    max_forecast_volatility: float = 0.045
    minimum_model_health: float = 0.80
    stale_after_minutes: int = 180


def decide_signal(inputs: SignalInputs, policy: SignalPolicy = SignalPolicy()) -> Signal:
    required = (
        inputs.direction_probability,
        inputs.forecast_volatility,
        inputs.model_health,
        inputs.prediction_generated_at,
    )
    if any(value is None for value in required):
        return Signal.NO_SIGNAL

    generated_at = inputs.prediction_generated_at
    assert generated_at is not None
    if generated_at.tzinfo is None:
        return Signal.NO_SIGNAL
    age_minutes = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds() / 60
    if age_minutes < 0 or age_minutes > policy.stale_after_minutes:
        return Signal.NO_SIGNAL

    probability = float(inputs.direction_probability)
    volatility = float(inputs.forecast_volatility)
    health = float(inputs.model_health)
    if not 0 <= probability <= 1 or volatility < 0 or not 0 <= health <= 1:
        return Signal.NO_SIGNAL
    if health < policy.minimum_model_health:
        return Signal.NO_SIGNAL
    if probability >= policy.buy_probability_min and volatility <= policy.max_forecast_volatility:
        return Signal.BUY
    if probability <= policy.avoid_probability_max or volatility > policy.max_forecast_volatility:
        return Signal.AVOID
    return Signal.HOLD
