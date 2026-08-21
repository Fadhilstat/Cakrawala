from datetime import UTC, datetime, timedelta

from cakrawala.intelligence.signals import Signal, SignalInputs, decide_signal


def inputs(probability: float, volatility: float, health: float = 0.9) -> SignalInputs:
    return SignalInputs(
        direction_probability=probability,
        forecast_volatility=volatility,
        model_health=health,
        prediction_generated_at=datetime.now(UTC),
    )


def test_buy_requires_probability_and_risk_gate() -> None:
    assert decide_signal(inputs(0.70, 0.02)) == Signal.BUY


def test_high_volatility_avoids() -> None:
    assert decide_signal(inputs(0.70, 0.08)) == Signal.AVOID


def test_stale_prediction_has_no_signal() -> None:
    stale = SignalInputs(
        direction_probability=0.9,
        forecast_volatility=0.01,
        model_health=0.95,
        prediction_generated_at=datetime.now(UTC) - timedelta(days=1),
    )
    assert decide_signal(stale) == Signal.NO_SIGNAL


def test_missing_evidence_has_no_signal() -> None:
    missing = SignalInputs(None, 0.01, 0.95, datetime.now(UTC))
    assert decide_signal(missing) == Signal.NO_SIGNAL
