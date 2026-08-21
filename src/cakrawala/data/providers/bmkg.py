from __future__ import annotations

from typing import Any

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult
from cakrawala.data.quality import require_mapping

EARTHQUAKE_URL = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
WEATHER_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"


def fetch_latest_earthquake() -> ProviderResult:
    policy = HttpPolicy(allowed_hosts=frozenset({"data.bmkg.go.id"}), max_bytes=1024 * 1024)
    response = get_json(EARTHQUAKE_URL, policy=policy)
    quality = require_mapping(response.payload, ("Infogempa",))
    if not quality.passed:
        raise ValueError(f"BMKG earthquake schema failed: {quality.errors}")
    return ProviderResult(
        provider="bmkg_earthquake",
        data=response.payload,
        provenance=build_provenance("bmkg_earthquake", response.url, response.raw),
    )


def fetch_weather(adm4: str) -> ProviderResult:
    if not adm4 or len(adm4) > 32:
        raise ValueError("adm4 must contain a valid administrative code")
    policy = HttpPolicy(allowed_hosts=frozenset({"api.bmkg.go.id"}))
    response = get_json(WEATHER_URL, policy=policy, params={"adm4": adm4})
    quality = require_mapping(response.payload, ("lokasi", "data"))
    if not quality.passed:
        raise ValueError(f"BMKG weather schema failed: {quality.errors}")
    return ProviderResult(
        provider="bmkg_weather",
        data=response.payload,
        provenance=build_provenance("bmkg_weather", response.url, response.raw),
    )


def earthquake_summary(payload: dict[str, Any]) -> dict[str, Any]:
    gempa = payload["Infogempa"]["gempa"]
    return {
        "magnitude": gempa.get("Magnitude"),
        "depth": gempa.get("Kedalaman"),
        "region": gempa.get("Wilayah"),
        "potential": gempa.get("Potensi"),
        "datetime": gempa.get("DateTime"),
    }
