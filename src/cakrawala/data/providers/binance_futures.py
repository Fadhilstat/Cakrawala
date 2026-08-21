from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult


BASE_URL = "https://fapi.binance.com"
_ALLOWED_PERIODS = {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}


@dataclass(frozen=True)
class FuturesPositioning:
    symbol: str
    long_account: float
    short_account: float
    long_short_ratio: float
    open_interest: float
    mark_price: float
    index_price: float
    last_funding_rate: float
    next_funding_time: datetime | None
    timestamp: datetime


def _policy() -> HttpPolicy:
    return HttpPolicy(
        allowed_hosts=frozenset({"fapi.binance.com"}),
        max_bytes=2 * 1024 * 1024,
    )


def _symbol(value: str) -> str:
    normalized = value.upper().strip()
    if not normalized.isalnum() or not 5 <= len(normalized) <= 24:
        raise ValueError("symbol must be an approved alphanumeric market symbol")
    return normalized


def _timestamp(milliseconds: Any) -> datetime:
    return datetime.fromtimestamp(int(milliseconds) / 1000, tz=UTC)


def fetch_global_long_short_ratio(
    symbol: str = "BTCUSDT",
    *,
    period: str = "1h",
    limit: int = 24,
) -> ProviderResult:
    market = _symbol(symbol)
    if period not in _ALLOWED_PERIODS:
        raise ValueError("period is not approved")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")

    url = f"{BASE_URL}/futures/data/globalLongShortAccountRatio"
    response = get_json(
        url,
        policy=_policy(),
        params={"symbol": market, "period": period, "limit": limit},
    )
    payload = response.payload
    if not isinstance(payload, list) or not payload:
        raise ValueError("Binance futures returned no long-short observations")
    required = {"symbol", "longShortRatio", "longAccount", "shortAccount", "timestamp"}
    if any(not isinstance(row, dict) or not required.issubset(row) for row in payload):
        raise ValueError("Binance long-short response failed schema validation")

    return ProviderResult(
        provider="binance_futures_positioning",
        data=payload,
        provenance=build_provenance(
            "binance_futures_positioning",
            response.url,
            response.raw,
        ),
    )


def fetch_open_interest(symbol: str = "BTCUSDT") -> ProviderResult:
    market = _symbol(symbol)
    url = f"{BASE_URL}/fapi/v1/openInterest"
    response = get_json(url, policy=_policy(), params={"symbol": market})
    payload = response.payload
    required = {"symbol", "openInterest", "time"}
    if not isinstance(payload, dict) or not required.issubset(payload):
        raise ValueError("Binance open-interest response failed schema validation")
    return ProviderResult(
        provider="binance_futures_open_interest",
        data=payload,
        provenance=build_provenance(
            "binance_futures_open_interest",
            response.url,
            response.raw,
        ),
    )


def fetch_premium_index(symbol: str = "BTCUSDT") -> ProviderResult:
    market = _symbol(symbol)
    url = f"{BASE_URL}/fapi/v1/premiumIndex"
    response = get_json(url, policy=_policy(), params={"symbol": market})
    payload = response.payload
    required = {
        "symbol",
        "markPrice",
        "indexPrice",
        "lastFundingRate",
        "nextFundingTime",
        "time",
    }
    if not isinstance(payload, dict) or not required.issubset(payload):
        raise ValueError("Binance premium-index response failed schema validation")
    return ProviderResult(
        provider="binance_futures_premium_index",
        data=payload,
        provenance=build_provenance(
            "binance_futures_premium_index",
            response.url,
            response.raw,
        ),
    )


def fetch_futures_positioning(symbol: str = "BTCUSDT") -> ProviderResult:
    market = _symbol(symbol)
    ratio = fetch_global_long_short_ratio(market, period="1h", limit=24)
    open_interest = fetch_open_interest(market)
    premium = fetch_premium_index(market)

    ratio_row = ratio.data[-1]
    open_row = open_interest.data
    premium_row = premium.data
    next_funding_raw = int(premium_row["nextFundingTime"])
    next_funding = _timestamp(next_funding_raw) if next_funding_raw > 0 else None
    latest = FuturesPositioning(
        symbol=market,
        long_account=float(ratio_row["longAccount"]),
        short_account=float(ratio_row["shortAccount"]),
        long_short_ratio=float(ratio_row["longShortRatio"]),
        open_interest=float(open_row["openInterest"]),
        mark_price=float(premium_row["markPrice"]),
        index_price=float(premium_row["indexPrice"]),
        last_funding_rate=float(premium_row["lastFundingRate"]),
        next_funding_time=next_funding,
        timestamp=_timestamp(ratio_row["timestamp"]),
    )
    raw = ratio.provenance.sha256.encode("ascii") + open_interest.provenance.sha256.encode(
        "ascii"
    ) + premium.provenance.sha256.encode("ascii")
    return ProviderResult(
        provider="binance_futures_context",
        data={
            "latest": latest,
            "ratio_history": ratio.data,
            "sources": {
                "ratio": ratio.provenance.source_url,
                "open_interest": open_interest.provenance.source_url,
                "premium_index": premium.provenance.source_url,
            },
        },
        provenance=build_provenance(
            "binance_futures_context",
            f"{BASE_URL}/futures/data/globalLongShortAccountRatio",
            raw,
        ),
    )
