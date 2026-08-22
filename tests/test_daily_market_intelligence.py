from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from cakrawala.data.http import JsonResponse
from cakrawala.data.providers import twelve_data
from cakrawala.intelligence.market_brief import MarketBias, assess_daily_prices


@dataclass(frozen=True)
class Point:
    observed_at: datetime
    close: float


def _series(start: float, steps: list[float], *, end: datetime) -> list[Point]:
    values = [start]
    for step in steps:
        values.append(values[-1] + step)
    first = end - timedelta(days=len(values) - 1)
    return [
        Point(observed_at=first + timedelta(days=index), close=value)
        for index, value in enumerate(values)
    ]


def test_daily_market_assessment_buy_bias_when_horizons_align() -> None:
    end = datetime(2026, 8, 21)
    points = _series(100, [1] * 20, end=end)
    result = assess_daily_prices("eurusd", points, today=end.date())
    assert result.bias == MarketBias.BUY_BIAS
    assert result.change_1d_pct is not None and result.change_1d_pct > 0
    assert result.change_5d_pct is not None and result.change_5d_pct > 0
    assert result.change_20d_pct is not None and result.change_20d_pct > 0


def test_daily_market_assessment_sell_bias_when_horizons_align() -> None:
    end = datetime(2026, 8, 21)
    points = _series(120, [-1] * 20, end=end)
    result = assess_daily_prices("USDJPY", points, today=end.date())
    assert result.bias == MarketBias.SELL_BIAS


def test_daily_market_assessment_waits_when_horizons_conflict() -> None:
    end = datetime(2026, 8, 21)
    points = _series(100, [1] * 15 + [-2] * 5, end=end)
    result = assess_daily_prices("GBPUSD", points, today=end.date())
    assert result.bias == MarketBias.WAIT


def test_daily_market_assessment_rejects_stale_or_future_data() -> None:
    end = datetime(2026, 8, 10)
    points = _series(100, [1] * 20, end=end)
    stale = assess_daily_prices("AUDUSD", points, today=datetime(2026, 8, 22).date())
    assert stale.bias == MarketBias.INSUFFICIENT

    future_points = _series(100, [1] * 20, end=datetime(2026, 8, 23))
    future = assess_daily_prices(
        "AUDUSD",
        future_points,
        today=datetime(2026, 8, 22).date(),
    )
    assert future.bias == MarketBias.INSUFFICIENT


def test_daily_market_assessment_requires_enough_completed_history() -> None:
    end = datetime(2026, 8, 21)
    points = _series(100, [1] * 10, end=end)
    result = assess_daily_prices("BBCA", points, today=end.date())
    assert result.bias == MarketBias.INSUFFICIENT


def test_twelve_data_requires_server_side_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TWELVE_DATA_API_KEY"):
        twelve_data.fetch_daily_equity_history("BBCA", mic_code="XIDX")


def test_twelve_data_rejects_unsafe_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "secret")
    with pytest.raises(ValueError, match="symbol"):
        twelve_data.fetch_daily_equity_history("BBCA&apikey=leak", mic_code="XIDX")


def test_twelve_data_rejects_ambiguous_venue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "secret")
    with pytest.raises(ValueError, match="either exchange or mic_code"):
        twelve_data.fetch_daily_equity_history(
            "AAPL",
            exchange="NASDAQ",
            mic_code="XNAS",
        )


def test_twelve_data_redacts_key_and_normalizes_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "top-secret")
    captured: dict[str, object] = {}
    values = []
    for index in range(21):
        price = 100 + index
        values.append(
            {
                "datetime": f"2026-07-{index + 1:02d}",
                "open": str(price),
                "high": str(price + 1),
                "low": str(price - 1),
                "close": str(price + 0.5),
                "volume": str(1000 + index),
            }
        )

    def fake_get_json(url: str, **kwargs: object) -> JsonResponse:
        captured["url"] = url
        captured.update(kwargs)
        return JsonResponse(
            url="https://api.twelvedata.com/time_series?apikey=%5BREDACTED%5D",
            status=200,
            content_type="application/json",
            payload={"meta": {"symbol": "BBCA"}, "values": list(reversed(values))},
            raw=b"{}",
        )

    monkeypatch.setattr(twelve_data, "get_json", fake_get_json)
    result = twelve_data.fetch_daily_equity_history("bbca", mic_code="xidx", outputsize=60)
    assert captured["sensitive_params"] == frozenset({"apikey"})
    assert "top-secret" not in result.provenance.source_url
    assert result.data["symbol"] == "BBCA"
    assert result.data["mic_code"] == "XIDX"
    assert result.data["exchange"] is None
    bars = result.data["bars"]
    assert len(bars) == 21
    assert bars[0].observed_at < bars[-1].observed_at


def test_twelve_data_rejects_invalid_ohlc_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "secret")

    def fake_get_json(url: str, **kwargs: object) -> JsonResponse:
        del url, kwargs
        return JsonResponse(
            url="https://api.twelvedata.com/time_series?apikey=%5BREDACTED%5D",
            status=200,
            content_type="application/json",
            payload={
                "values": [
                    {
                        "datetime": "2026-08-21",
                        "open": "100",
                        "high": "90",
                        "low": "80",
                        "close": "95",
                    },
                    {
                        "datetime": "2026-08-20",
                        "open": "98",
                        "high": "99",
                        "low": "97",
                        "close": "98.5",
                    },
                ]
            },
            raw=b"{}",
        )

    monkeypatch.setattr(twelve_data, "get_json", fake_get_json)
    with pytest.raises(ValueError, match="internally inconsistent"):
        twelve_data.fetch_daily_equity_history("AAPL")
