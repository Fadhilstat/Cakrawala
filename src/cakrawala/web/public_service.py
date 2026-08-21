from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from math import sqrt
from typing import Any

import pandas as pd

from cakrawala.web.cache import PUBLIC_CACHE


def _safe_load(name: str, loader: Callable[[], Any], snapshot: dict[str, Any]) -> None:
    try:
        snapshot[name] = loader()
    except Exception as exc:
        snapshot[name] = None
        snapshot["errors"][name] = type(exc).__name__


def load_earthquake() -> dict[str, Any]:
    from cakrawala.data.providers.bmkg import earthquake_summary, fetch_latest_earthquake

    def loader() -> dict[str, Any]:
        result = fetch_latest_earthquake()
        return {
            **earthquake_summary(result.data),
            "fetched_at": result.provenance.fetched_at,
            "source_url": result.provenance.source_url,
        }

    return PUBLIC_CACHE.get("earthquake", 600, loader)


def load_macro_indicator(indicator: str, date_range: str = "2018:2024") -> dict[str, Any]:
    from cakrawala.data.providers.world_bank import fetch_indicator

    def loader() -> dict[str, Any]:
        result = fetch_indicator("IDN", indicator, date_range)
        rows = result.data[1] if len(result.data) > 1 else []
        observations = [
            {"year": int(row["date"]), "value": float(row["value"])}
            for row in rows
            if isinstance(row, dict)
            and row.get("value") is not None
            and str(row.get("date", "")).isdigit()
        ]
        observations.sort(key=lambda row: row["year"])
        if not observations:
            raise ValueError("World Bank returned no usable observations")
        return {
            "observations": observations,
            "latest": observations[-1],
            "fetched_at": result.provenance.fetched_at,
            "source_url": result.provenance.source_url,
        }

    key = f"macro:{indicator}:{date_range}"
    return PUBLIC_CACHE.get(key, 1800, loader)


def load_market_history(symbol: str = "BTCUSDT", limit: int = 90) -> dict[str, Any]:
    from cakrawala.data.providers.binance import fetch_klines

    market = symbol.upper().strip()
    if not market.isalnum() or len(market) > 24:
        raise ValueError("market symbol is invalid")

    def loader() -> dict[str, Any]:
        result = fetch_klines(market, interval="1d", limit=limit)
        records: list[dict[str, Any]] = []
        for row in result.data:
            if not isinstance(row, list) or len(row) < 7:
                continue
            records.append(
                {
                    "time": pd.to_datetime(int(row[0]), unit="ms", utc=True),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        if len(records) < 2:
            raise ValueError("Binance returned insufficient market history")
        frame = pd.DataFrame(records).sort_values("time").reset_index(drop=True)
        frame["return"] = frame["close"].pct_change()
        latest = frame.iloc[-1]
        previous = frame.iloc[-2]
        return {
            "frame": frame,
            "latest": {
                "close": float(latest["close"]),
                "volume": float(latest["volume"]),
                "change_1d_pct": (
                    float(latest["close"]) / float(previous["close"]) - 1.0
                )
                * 100,
            },
            "fetched_at": result.provenance.fetched_at,
            "source_url": result.provenance.source_url,
        }

    return PUBLIC_CACHE.get(f"market:{market}:{limit}", 300, loader)


def load_news() -> list[dict[str, Any]]:
    from cakrawala.data.providers.news_feeds import fetch_macro_news
    from cakrawala.intelligence.news import assess_news

    def loader() -> list[dict[str, Any]]:
        items = fetch_macro_news(limit_per_source=8)
        return [asdict(item) for item in assess_news(items)]

    return PUBLIC_CACHE.get("news", 600, loader)


def load_futures_context() -> dict[str, Any]:
    from cakrawala.data.providers.binance_futures import fetch_futures_positioning

    def loader() -> dict[str, Any]:
        result = fetch_futures_positioning("BTCUSDT")
        return {
            "latest": asdict(result.data["latest"]),
            "ratio_history": result.data["ratio_history"],
            "sources": result.data["sources"],
            "fetched_at": result.provenance.fetched_at,
        }

    return PUBLIC_CACHE.get("futures:BTCUSDT", 300, loader)


def load_economic_calendar(days_ahead: int = 14) -> list[dict[str, Any]]:
    from cakrawala.data.providers.bls_calendar import fetch_bls_calendar

    def loader() -> list[dict[str, Any]]:
        result = fetch_bls_calendar()
        now = datetime.now(UTC)
        cutoff = now + timedelta(days=days_ahead)
        events = [event for event in result.data if now <= event.starts_at <= cutoff]
        return [asdict(event) for event in events[:30]]

    return PUBLIC_CACHE.get(f"calendar:{days_ahead}", 1800, loader)


def load_cot_context() -> list[dict[str, Any]]:
    from cakrawala.data.providers.cftc import fetch_tff_market

    def loader() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for market in ("EURO FX", "U.S. DOLLAR INDEX", "NASDAQ-100"):
            try:
                result = fetch_tff_market(market)
            except Exception:
                continue
            latest = result.data[0]
            previous = result.data[1] if len(result.data) > 1 else None
            item = asdict(latest)
            item["asset_manager_change"] = (
                latest.asset_manager_net - previous.asset_manager_net if previous else None
            )
            item["leveraged_funds_change"] = (
                latest.leveraged_funds_net - previous.leveraged_funds_net if previous else None
            )
            item["source_url"] = result.provenance.source_url
            rows.append(item)
        if not rows:
            raise ValueError("CFTC returned no configured institutional markets")
        return rows

    return PUBLIC_CACHE.get("cot", 21600, loader)


def load_currency_strength() -> list[dict[str, object]]:
    from cakrawala.data.providers.ecb_fx import fetch_currency_strength

    def loader() -> list[dict[str, object]]:
        return [asdict(item) for item in fetch_currency_strength().data]

    return PUBLIC_CACHE.get("ecb_fx", 900, loader)


def market_risk_stats(frame: pd.DataFrame) -> dict[str, float | None]:
    returns = frame["return"].dropna()
    closes = frame["close"].astype(float)
    if returns.empty:
        return {"volatility": None, "drawdown": None, "momentum": None}
    last_30 = returns.tail(30)
    volatility = None
    if len(last_30) > 1:
        volatility = float(last_30.std(ddof=1) * sqrt(365) * 100)
    drawdown = float((closes.iloc[-1] / closes.cummax().iloc[-1] - 1.0) * 100)
    lookback = max(len(closes) - 31, 0)
    momentum = float((closes.iloc[-1] / closes.iloc[lookback] - 1.0) * 100)
    return {"volatility": volatility, "drawdown": drawdown, "momentum": momentum}


def public_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {"errors": {}, "generated_at": datetime.now(UTC)}
    _safe_load("earthquake", load_earthquake, snapshot)
    _safe_load("population", lambda: load_macro_indicator("SP.POP.TOTL"), snapshot)
    _safe_load("gdp", lambda: load_macro_indicator("NY.GDP.MKTP.KD.ZG"), snapshot)
    _safe_load("inflation", lambda: load_macro_indicator("FP.CPI.TOTL.ZG"), snapshot)
    _safe_load("market", load_market_history, snapshot)
    _safe_load("news", load_news, snapshot)
    _safe_load("futures", load_futures_context, snapshot)
    _safe_load("calendar", load_economic_calendar, snapshot)
    _safe_load("cot", load_cot_context, snapshot)
    _safe_load("currency_strength", load_currency_strength, snapshot)
    return snapshot
