from __future__ import annotations

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult

BASE_URL = "https://data-api.binance.vision/api/v3"


def fetch_klines(symbol: str, interval: str = "1d", limit: int = 500) -> ProviderResult:
    if not symbol.isalnum() or len(symbol) > 24:
        raise ValueError("symbol must be alphanumeric")
    if interval not in {"1h", "4h", "1d", "1w"}:
        raise ValueError("interval is not approved")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    policy = HttpPolicy(allowed_hosts=frozenset({"data-api.binance.vision"}))
    response = get_json(
        f"{BASE_URL}/klines",
        policy=policy,
        params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
    )
    if not isinstance(response.payload, list) or not response.payload:
        raise ValueError("Binance returned an empty or invalid kline payload")
    return ProviderResult(
        provider="binance_market_data",
        data=response.payload,
        provenance=build_provenance("binance_market_data", response.url, response.raw),
    )
