from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult

TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,19}$")
_EXCHANGE_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,15}$")
_MIC_RE = re.compile(r"^[A-Z0-9]{4}$")


@dataclass(frozen=True)
class DailyMarketBar:
    observed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None


def _validated_identifier(value: str, *, label: str, pattern: re.Pattern[str]) -> str:
    normalized = value.strip().upper()
    if not normalized or pattern.fullmatch(normalized) is None:
        raise ValueError(f"{label} contains unsupported characters")
    return normalized


def _parse_number(value: object, *, label: str) -> float:
    try:
        parsed = float(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Twelve Data {label} is not numeric") from exc
    return parsed


def _parse_daily_values(payload: object) -> list[DailyMarketBar]:
    if not isinstance(payload, dict):
        raise ValueError("Twelve Data response failed schema validation")
    if payload.get("status") == "error":
        raise RuntimeError("Twelve Data returned an API error")
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise ValueError("Twelve Data response contained no time-series values")

    bars_by_time: dict[datetime, DailyMarketBar] = {}
    for item in values:
        if not isinstance(item, dict):
            raise ValueError("Twelve Data time-series row failed schema validation")
        try:
            observed_at = datetime.fromisoformat(str(item["datetime"]))
        except (KeyError, ValueError) as exc:
            raise ValueError("Twelve Data datetime failed validation") from exc
        open_price = _parse_number(item.get("open"), label="open")
        high = _parse_number(item.get("high"), label="high")
        low = _parse_number(item.get("low"), label="low")
        close = _parse_number(item.get("close"), label="close")
        if min(open_price, high, low, close) <= 0:
            raise ValueError("Twelve Data OHLC values must be positive")
        if high < max(open_price, close, low) or low > min(open_price, close, high):
            raise ValueError("Twelve Data OHLC values are internally inconsistent")

        raw_volume = item.get("volume")
        volume = None if raw_volume in (None, "") else _parse_number(raw_volume, label="volume")
        if volume is not None and volume < 0:
            raise ValueError("Twelve Data volume must not be negative")
        bars_by_time[observed_at] = DailyMarketBar(
            observed_at=observed_at,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

    bars = sorted(bars_by_time.values(), key=lambda item: item.observed_at)
    if len(bars) < 2:
        raise ValueError("Twelve Data response contained insufficient history")
    return bars


def fetch_daily_equity_history(
    symbol: str,
    *,
    exchange: str | None = None,
    mic_code: str | None = None,
    outputsize: int = 60,
) -> ProviderResult:
    api_key = os.environ.get("TWELVE_DATA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured")
    normalized_symbol = _validated_identifier(symbol, label="symbol", pattern=_SYMBOL_RE)
    if exchange is not None and mic_code is not None:
        raise ValueError("configure either exchange or mic_code, not both")
    if outputsize < 21 or outputsize > 120:
        raise ValueError("outputsize must be between 21 and 120")

    params: dict[str, str | int | float] = {
        "symbol": normalized_symbol,
        "interval": "1day",
        "outputsize": outputsize,
        "order": "asc",
        "format": "JSON",
        "apikey": api_key,
    }
    normalized_exchange = None
    normalized_mic = None
    if exchange is not None:
        normalized_exchange = _validated_identifier(
            exchange,
            label="exchange",
            pattern=_EXCHANGE_RE,
        )
        params["exchange"] = normalized_exchange
    if mic_code is not None:
        normalized_mic = _validated_identifier(
            mic_code,
            label="mic_code",
            pattern=_MIC_RE,
        )
        params["mic_code"] = normalized_mic

    policy = HttpPolicy(
        allowed_hosts=frozenset({"api.twelvedata.com"}),
        timeout_seconds=10,
        max_bytes=2 * 1024 * 1024,
        attempts=3,
    )
    response = get_json(
        TWELVE_DATA_URL,
        policy=policy,
        params=params,
        sensitive_params=frozenset({"apikey"}),
    )
    bars = _parse_daily_values(response.payload)
    provider_name = "twelve_data_personal_equity"
    return ProviderResult(
        provider=provider_name,
        data={
            "symbol": normalized_symbol,
            "exchange": normalized_exchange,
            "mic_code": normalized_mic,
            "bars": bars,
        },
        provenance=build_provenance(provider_name, response.url, response.raw),
    )
