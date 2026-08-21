from __future__ import annotations

import os

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult


def fetch_fred_series(series_id: str) -> ProviderResult:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not configured")
    if not series_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("series_id contains unsupported characters")
    url = "https://api.stlouisfed.org/fred/series/observations"
    policy = HttpPolicy(allowed_hosts=frozenset({"api.stlouisfed.org"}))
    response = get_json(
        url,
        policy=policy,
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        sensitive_params=frozenset({"api_key"}),
    )
    if not isinstance(response.payload, dict) or "observations" not in response.payload:
        raise ValueError("FRED response failed schema validation")
    return ProviderResult(
        provider="fred",
        data=response.payload,
        provenance=build_provenance("fred", response.url, response.raw),
    )


def bps_api_key() -> str:
    api_key = os.environ.get("BPS_API_KEY")
    if not api_key:
        raise RuntimeError("BPS_API_KEY is not configured")
    return api_key
