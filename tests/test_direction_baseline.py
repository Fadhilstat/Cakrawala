from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from cakrawala.models.direction_baseline import (
    BacktestConfig,
    build_direction_dataset,
    walk_forward_backtest,
)
from scripts.run_model_backtest import _frame_from_klines


def _market_frame(rows: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(17)
    returns = rng.normal(0.0005, 0.018, rows)
    close = 100 * np.cumprod(1 + returns)
    open_price = np.r_[100.0, close[:-1]]
    high = np.maximum(open_price, close) * (1 + rng.uniform(0.0, 0.01, rows))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0.0, 0.01, rows))
    volume = rng.lognormal(10.0, 0.35, rows)
    return pd.DataFrame(
        {
            "open_time": pd.date_range("2023-01-01", periods=rows, freq="D", tz="UTC"),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def _millis(value: str) -> int:
    return int(pd.Timestamp(value).timestamp() * 1000)


def test_binance_parser_excludes_incomplete_daily_candle() -> None:
    fetched_at = datetime(2026, 8, 21, 18, 42, tzinfo=UTC)
    rows: list[list[object]] = [
        [
            _millis("2026-08-20T00:00:00Z"),
            "100",
            "105",
            "95",
            "103",
            "10",
            _millis("2026-08-20T23:59:59.999Z"),
        ],
        [
            _millis("2026-08-21T00:00:00Z"),
            "103",
            "108",
            "101",
            "106",
            "11",
            _millis("2026-08-21T23:59:59.999Z"),
        ],
    ]
    frame = _frame_from_klines(rows, fetched_at)
    assert len(frame) == 1
    assert frame["open_time"].iloc[0] == pd.Timestamp("2026-08-20T00:00:00Z")
    assert frame["close_time"].iloc[0] < pd.Timestamp(fetched_at)


def test_direction_dataset_uses_only_completed_history() -> None:
    frame = _market_frame(200)
    dataset = build_direction_dataset(frame)
    assert not dataset.empty
    assert dataset["open_time"].is_monotonic_increasing
    assert dataset["open_time"].is_unique
    assert (dataset["next_open_time"] > dataset["open_time"]).all()
    assert dataset["next_session_return"].notna().all()
    assert (
        dataset["target_up"]
        == (dataset["next_close"] > dataset["next_open"]).astype(int)
    ).all()


def test_walk_forward_backtest_is_complete_and_deterministic() -> None:
    frame = _market_frame()
    config = BacktestConfig(minimum_train_rows=365, retrain_every=30)
    first = walk_forward_backtest(frame, config)
    second = walk_forward_backtest(frame, config)
    assert first.to_dict() == second.to_dict()
    assert first.observations > 400
    assert first.diagnostics["prediction_coverage"] == pytest.approx(1.0)
    assert first.diagnostics["lookahead_detected"] is False
    assert (
        first.diagnostics["signal_timing"]
        == "features_at_close_t_trade_open_to_close_t_plus_1"
    )
    assert first.promotion_inputs["walk_forward_complete"] is True
    assert first.promotion_inputs["point_in_time_features"] is True


def test_backtest_rejects_duplicate_timestamps() -> None:
    frame = _market_frame()
    frame.loc[1, "open_time"] = frame.loc[0, "open_time"]
    with pytest.raises(ValueError, match="duplicate open_time"):
        walk_forward_backtest(frame)
