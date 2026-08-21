from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from math import sqrt
from typing import Any

import pandas as pd
import streamlit as st

from cakrawala.data.providers.binance import fetch_klines
from cakrawala.data.providers.binance_futures import fetch_futures_positioning
from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.bmkg import earthquake_summary, fetch_latest_earthquake
from cakrawala.data.providers.cftc import fetch_tff_market
from cakrawala.data.providers.news_feeds import fetch_macro_news
from cakrawala.data.providers.world_bank import fetch_indicator
from cakrawala.intelligence.news import assess_news


@st.cache_data(ttl=600, show_spinner=False)
def load_earthquake() -> dict[str, Any]:
    result = fetch_latest_earthquake()
    summary = earthquake_summary(result.data)
    return {
        **summary,
        "fetched_at": result.provenance.fetched_at,
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_macro_indicator(
    indicator: str,
    date_range: str = "2018:2024",
) -> dict[str, Any]:
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


@st.cache_data(ttl=300, show_spinner=False)
def load_market_history(limit: int = 90) -> dict[str, Any]:
    result = fetch_klines("BTCUSDT", interval="1d", limit=limit)
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
    change_pct = (float(latest["close"]) / float(previous["close"]) - 1.0) * 100
    return {
        "frame": frame,
        "latest": {
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
            "change_1d_pct": change_pct,
        },
        "fetched_at": result.provenance.fetched_at,
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=600, show_spinner=False)
def load_news() -> list[dict[str, Any]]:
    items = fetch_macro_news(limit_per_source=8)
    return [asdict(item) for item in assess_news(items)]


@st.cache_data(ttl=300, show_spinner=False)
def load_futures_context() -> dict[str, Any]:
    result = fetch_futures_positioning("BTCUSDT")
    return {
        "latest": asdict(result.data["latest"]),
        "ratio_history": result.data["ratio_history"],
        "sources": result.data["sources"],
        "fetched_at": result.provenance.fetched_at,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_economic_calendar(days_ahead: int = 14) -> list[dict[str, Any]]:
    result = fetch_bls_calendar()
    now = datetime.now(UTC)
    cutoff = now + timedelta(days=days_ahead)
    upcoming = [event for event in result.data if now <= event.starts_at <= cutoff]
    return [asdict(event) for event in upcoming[:30]]


@st.cache_data(ttl=21600, show_spinner=False)
def load_cot_context() -> list[dict[str, Any]]:
    markets = (
        "EURO FX",
        "U.S. DOLLAR INDEX",
        "NASDAQ-100",
    )
    rows: list[dict[str, Any]] = []
    for market in markets:
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
    return {
        "volatility": volatility,
        "drawdown": drawdown,
        "momentum": momentum,
    }


def _safe_load(
    name: str,
    loader: Callable[[], Any],
    snapshot: dict[str, Any],
) -> None:
    try:
        snapshot[name] = loader()
    except Exception as exc:
        snapshot[name] = None
        snapshot["errors"][name] = type(exc).__name__


def public_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {"errors": {}}
    _safe_load("earthquake", load_earthquake, snapshot)
    _safe_load("population", lambda: load_macro_indicator("SP.POP.TOTL"), snapshot)
    _safe_load("gdp", lambda: load_macro_indicator("NY.GDP.MKTP.KD.ZG"), snapshot)
    _safe_load("inflation", lambda: load_macro_indicator("FP.CPI.TOTL.ZG"), snapshot)
    _safe_load("market", load_market_history, snapshot)
    _safe_load("news", load_news, snapshot)
    _safe_load("futures", load_futures_context, snapshot)
    _safe_load("calendar", load_economic_calendar, snapshot)
    _safe_load("cot", load_cot_context, snapshot)
    return snapshot
