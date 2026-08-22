from __future__ import annotations

import pytest

from cakrawala.models.fx_foundation import evaluate_series, walk_forward_origins


def test_walk_forward_origins_are_point_in_time() -> None:
    origins = walk_forward_origins(400, min_context=256, horizon=5, count=6)
    assert origins[0] >= 256
    assert origins[-1] <= 395
    assert origins == sorted(origins)


def test_evaluate_series_compares_against_last_value_baseline() -> None:
    values = [100.0 + index * 0.1 for index in range(320)]

    def forecaster(
        context: list[float],
        horizon: int,
    ) -> tuple[list[float], list[float], list[float]]:
        last = context[-1]
        median = [last + 0.1 * (step + 1) for step in range(horizon)]
        low = [value - 0.05 for value in median]
        high = [value + 0.05 for value in median]
        return low, median, high

    metrics = evaluate_series(values, forecaster, horizon=5, min_context=256, origins=4)
    assert metrics.observations == 20
    assert metrics.mae == pytest.approx(0.0, abs=1e-10)
    assert metrics.baseline_mae > 0
    assert metrics.mae_improvement == pytest.approx(1.0)
    assert metrics.direction_accuracy == pytest.approx(1.0)
    assert metrics.interval_coverage == pytest.approx(1.0)


def test_invalid_forecast_horizon_is_rejected() -> None:
    values = [float(index) for index in range(300)]

    def bad_forecaster(
        context: list[float], horizon: int
    ) -> tuple[list[float], list[float], list[float]]:
        del context, horizon
        return [1.0], [1.0], [1.0]

    with pytest.raises(ValueError, match="invalid horizon"):
        evaluate_series(values, bad_forecaster, horizon=5, min_context=256, origins=2)
