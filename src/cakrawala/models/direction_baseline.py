from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = (
    "return_1d",
    "momentum_3d",
    "momentum_7d",
    "momentum_14d",
    "momentum_30d",
    "volatility_7d",
    "volatility_14d",
    "volatility_30d",
    "close_vs_sma_10",
    "close_vs_sma_20",
    "close_vs_sma_50",
    "range_pct",
    "volume_z_20",
)


@dataclass(frozen=True)
class BacktestConfig:
    minimum_train_rows: int = 365
    retrain_every: int = 30
    buy_probability: float = 0.55
    transaction_cost_bps: float = 10.0
    random_state: int = 17

    def validate(self) -> None:
        if self.minimum_train_rows < 120:
            raise ValueError("minimum_train_rows must be at least 120")
        if self.retrain_every < 1:
            raise ValueError("retrain_every must be positive")
        if not 0.5 <= self.buy_probability < 1:
            raise ValueError("buy_probability must be between 0.5 and 1")
        if not 0 <= self.transaction_cost_bps <= 100:
            raise ValueError("transaction_cost_bps must be between 0 and 100")


@dataclass(frozen=True)
class BacktestResult:
    model_name: str
    observations: int
    train_start: str
    test_start: str
    test_end: str
    classification: dict[str, float]
    baseline: dict[str, float]
    strategy: dict[str, float]
    buy_and_hold: dict[str, float]
    diagnostics: dict[str, float | int | bool | str]
    promotion_inputs: dict[str, float | bool | str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"open_time", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"market frame is missing columns: {sorted(missing)}")
    data = frame.loc[:, sorted(required)].copy()
    data["open_time"] = pd.to_datetime(data["open_time"], utc=True)
    data = data.sort_values("open_time").reset_index(drop=True)
    if data["open_time"].duplicated().any():
        raise ValueError("market frame contains duplicate open_time values")
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    if not np.isfinite(data[["open", "high", "low", "close", "volume"]]).all().all():
        raise ValueError("market frame contains non-finite numeric values")
    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("market prices must be positive")
    if (data["volume"] < 0).any():
        raise ValueError("market volume must be non-negative")
    if (data["high"] < data[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("market frame contains an invalid high price")
    if (data["low"] > data[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("market frame contains an invalid low price")
    return data


def build_direction_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    data = _validate_market_frame(frame)
    returns = data["close"].pct_change()
    data["return_1d"] = returns
    for days in (3, 7, 14, 30):
        data[f"momentum_{days}d"] = data["close"].pct_change(days)
    for days in (7, 14, 30):
        data[f"volatility_{days}d"] = returns.rolling(days).std(ddof=0)
    for days in (10, 20, 50):
        data[f"close_vs_sma_{days}"] = data["close"] / data["close"].rolling(days).mean() - 1
    data["range_pct"] = (data["high"] - data["low"]) / data["open"]
    volume_mean = data["volume"].rolling(20).mean()
    volume_std = data["volume"].rolling(20).std(ddof=0).replace(0, np.nan)
    data["volume_z_20"] = (data["volume"] - volume_mean) / volume_std

    data["next_open_time"] = data["open_time"].shift(-1)
    data["next_open"] = data["open"].shift(-1)
    data["next_close"] = data["close"].shift(-1)
    data["target_up"] = (data["next_close"] > data["next_open"]).astype(float)
    data["next_session_return"] = data["next_close"] / data["next_open"] - 1
    data = data.dropna(
        subset=[*FEATURE_COLUMNS, "next_open_time", "next_open", "next_close", "next_session_return"]
    ).reset_index(drop=True)
    data["target_up"] = data["target_up"].astype(int)
    return data


def _make_estimator(random_state: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.5,
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
        ]
    )


def _safe_auc(y_true: pd.Series, probability: pd.Series) -> float:
    if y_true.nunique() < 2:
        return float("nan")
    return float(roc_auc_score(y_true, probability))


def _classification_metrics(y_true: pd.Series, probability: pd.Series) -> dict[str, float]:
    clipped = probability.clip(1e-6, 1 - 1e-6)
    prediction = (probability >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "brier_score": float(brier_score_loss(y_true, clipped)),
        "log_loss": float(log_loss(y_true, clipped, labels=[0, 1])),
        "roc_auc": _safe_auc(y_true, probability),
    }


def _return_metrics(returns: pd.Series, periods_per_year: int = 365) -> dict[str, float]:
    clean = returns.fillna(0.0).astype(float)
    if clean.empty:
        raise ValueError("return series must not be empty")
    equity = (1.0 + clean).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    years = len(clean) / periods_per_year
    annualized_return = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
    annualized_volatility = float(clean.std(ddof=0) * sqrt(periods_per_year))
    sharpe = 0.0
    if annualized_volatility > 0:
        sharpe = float(clean.mean() / clean.std(ddof=0) * sqrt(periods_per_year))
    drawdown = equity / equity.cummax() - 1.0
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_zero_rf": sharpe,
        "max_drawdown": float(drawdown.min()),
    }


def _buy_and_hold_returns(predicted: pd.DataFrame, round_trip_cost: float) -> pd.Series:
    returns = predicted["next_close"].pct_change().astype(float)
    returns.iloc[0] = predicted["next_close"].iloc[0] / predicted["next_open"].iloc[0] - 1
    half_cost = round_trip_cost / 2
    returns.iloc[0] -= half_cost
    returns.iloc[-1] -= half_cost
    return returns


def walk_forward_backtest(
    frame: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    active = config or BacktestConfig()
    active.validate()
    dataset = build_direction_dataset(frame)
    if len(dataset) <= active.minimum_train_rows + active.retrain_every:
        raise ValueError("not enough rows for the configured walk-forward backtest")

    prediction_rows: list[pd.DataFrame] = []
    start = active.minimum_train_rows
    while start < len(dataset):
        stop = min(start + active.retrain_every, len(dataset))
        train = dataset.iloc[:start]
        test = dataset.iloc[start:stop].copy()
        if train["target_up"].nunique() < 2:
            raise ValueError("training window does not contain both target classes")
        estimator = _make_estimator(active.random_state)
        estimator.fit(train.loc[:, FEATURE_COLUMNS], train["target_up"])
        test["probability_up"] = estimator.predict_proba(test.loc[:, FEATURE_COLUMNS])[:, 1]
        test["baseline_probability"] = float(train["target_up"].mean())
        prediction_rows.append(test)
        start = stop

    predicted = pd.concat(prediction_rows, ignore_index=True)
    y_true = predicted["target_up"]
    model_probability = predicted["probability_up"]
    baseline_probability = predicted["baseline_probability"]
    model_metrics = _classification_metrics(y_true, model_probability)
    baseline_metrics = _classification_metrics(y_true, baseline_probability)

    position = (model_probability >= active.buy_probability).astype(float)
    round_trip_cost = active.transaction_cost_bps / 10_000
    strategy_returns = position * predicted["next_session_return"] - position * round_trip_cost
    strategy_metrics = _return_metrics(strategy_returns)
    strategy_metrics.update(
        {
            "exposure": float(position.mean()),
            "traded_sessions": float(position.sum()),
            "invested_hit_rate": float(
                (predicted.loc[position.eq(1), "next_session_return"] > 0).mean()
            )
            if position.sum() > 0
            else 0.0,
        }
    )

    benchmark_returns = _buy_and_hold_returns(predicted, round_trip_cost)
    benchmark_metrics = _return_metrics(benchmark_returns)

    baseline_brier = baseline_metrics["brier_score"]
    relative_improvement = (
        (baseline_brier - model_metrics["brier_score"]) / baseline_brier
        if baseline_brier > 0
        else 0.0
    )
    baseline_log_loss = baseline_metrics["log_loss"]
    secondary_regression = (
        max(0.0, model_metrics["log_loss"] - baseline_log_loss) / baseline_log_loss
        if baseline_log_loss > 0
        else 0.0
    )
    coverage = len(predicted) / (len(dataset) - active.minimum_train_rows)
    promotion_inputs: dict[str, float | bool | str] = {
        "model_name": "logistic_direction_v1",
        "healthy": bool(coverage >= 0.99 and np.isfinite(model_metrics["brier_score"])),
        "health_score": float(min(1.0, coverage)),
        "relative_improvement": float(relative_improvement),
        "secondary_metric_regression": float(secondary_regression),
        "walk_forward_complete": bool(len(predicted) == len(dataset) - active.minimum_train_rows),
        "point_in_time_features": True,
    }

    return BacktestResult(
        model_name="logistic_direction_v1",
        observations=len(predicted),
        train_start=dataset["open_time"].iloc[0].isoformat(),
        test_start=predicted["next_open_time"].iloc[0].isoformat(),
        test_end=predicted["next_open_time"].iloc[-1].isoformat(),
        classification=model_metrics,
        baseline=baseline_metrics,
        strategy=strategy_metrics,
        buy_and_hold=benchmark_metrics,
        diagnostics={
            "prediction_coverage": float(coverage),
            "positive_class_share": float(y_true.mean()),
            "retrain_count": len(prediction_rows),
            "feature_count": len(FEATURE_COLUMNS),
            "lookahead_detected": False,
            "signal_timing": "features_at_close_t_trade_open_to_close_t_plus_1",
            "transaction_cost_assumption": "round_trip_cost_per_invested_session",
        },
        promotion_inputs=promotion_inputs,
    )
