from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Callable


@dataclass(frozen=True)
class ForecastPoint:
    actual: float
    median: float
    low: float
    high: float
    previous: float


@dataclass(frozen=True)
class ForecastMetrics:
    observations: int
    mae: float
    baseline_mae: float
    mae_improvement: float
    direction_accuracy: float
    baseline_direction_accuracy: float
    interval_coverage: float


def evaluate_forecasts(points: list[ForecastPoint]) -> ForecastMetrics:
    if not points:
        raise ValueError("forecast evaluation requires observations")

    absolute_errors = [abs(item.median - item.actual) for item in points]
    baseline_errors = [abs(item.previous - item.actual) for item in points]
    model_direction = [
        (item.median - item.previous) * (item.actual - item.previous) > 0
        for item in points
    ]
    baseline_direction = [item.actual == item.previous for item in points]
    coverage = [item.low <= item.actual <= item.high for item in points]

    model_mae = mean(absolute_errors)
    baseline_mae = mean(baseline_errors)
    improvement = 0.0
    if baseline_mae > 0:
        improvement = 1.0 - model_mae / baseline_mae

    return ForecastMetrics(
        observations=len(points),
        mae=model_mae,
        baseline_mae=baseline_mae,
        mae_improvement=improvement,
        direction_accuracy=mean(model_direction),
        baseline_direction_accuracy=mean(baseline_direction),
        interval_coverage=mean(coverage),
    )


def walk_forward_origins(length: int, *, min_context: int, horizon: int, count: int) -> list[int]:
    if min_context <= 0 or horizon <= 0 or count <= 0:
        raise ValueError("walk-forward settings must be positive")
    last_origin = length - horizon
    if last_origin < min_context:
        raise ValueError("series is too short for requested walk-forward evaluation")
    available = last_origin - min_context + 1
    if count >= available:
        return list(range(min_context, last_origin + 1))
    step = max((available - 1) // (count - 1), 1) if count > 1 else 1
    origins = list(range(min_context, last_origin + 1, step))[:count]
    if origins[-1] != last_origin and len(origins) < count:
        origins.append(last_origin)
    return origins


def evaluate_series(
    values: list[float],
    forecaster: Callable[[list[float], int], tuple[list[float], list[float], list[float]]],
    *,
    horizon: int = 5,
    min_context: int = 256,
    origins: int = 12,
) -> ForecastMetrics:
    points: list[ForecastPoint] = []
    for origin in walk_forward_origins(
        len(values), min_context=min_context, horizon=horizon, count=origins
    ):
        context = values[:origin]
        low, median, high = forecaster(context, horizon)
        if not (len(low) == len(median) == len(high) == horizon):
            raise ValueError("forecaster returned an invalid horizon")
        previous = context[-1]
        actuals = values[origin : origin + horizon]
        for actual, low_value, median_value, high_value in zip(
            actuals, low, median, high, strict=True
        ):
            points.append(
                ForecastPoint(
                    actual=float(actual),
                    median=float(median_value),
                    low=float(low_value),
                    high=float(high_value),
                    previous=float(previous),
                )
            )
            previous = float(actual)
    return evaluate_forecasts(points)
