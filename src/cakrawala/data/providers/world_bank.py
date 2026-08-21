from __future__ import annotations

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult
from cakrawala.data.quality import require_sequence

BASE_URL = "https://api.worldbank.org/v2"


def fetch_indicator(country: str, indicator: str, date: str | None = None) -> ProviderResult:
    if not country.replace(";", "").isalnum():
        raise ValueError("country contains unsupported characters")
    if not indicator.replace(".", "").isalnum():
        raise ValueError("indicator contains unsupported characters")
    url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    params: dict[str, str | int] = {"format": "json", "per_page": 200}
    if date:
        params["date"] = date
    policy = HttpPolicy(allowed_hosts=frozenset({"api.worldbank.org"}))
    response = get_json(url, policy=policy, params=params)
    quality = require_sequence(response.payload, minimum_items=2)
    if not quality.passed:
        raise ValueError(f"World Bank schema failed: {quality.errors}")
    return ProviderResult(
        provider="world_bank",
        data=response.payload,
        provenance=build_provenance("world_bank", response.url, response.raw),
    )
