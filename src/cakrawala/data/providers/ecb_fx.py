from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from xml.etree import ElementTree

from cakrawala.data.http import HttpPolicy, get_text
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult

ECB_90D_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"


@dataclass(frozen=True)
class FxStrength:
    currency: str
    change_1d_pct: float | None
    change_5d_pct: float | None
    change_20d_pct: float | None
    as_of: date


def _change(values: list[float], periods: int) -> float | None:
    if len(values) <= periods:
        return None
    latest = values[-1]
    previous = values[-1 - periods]
    if previous == 0:
        return None
    return -((latest / previous) - 1.0) * 100


def parse_ecb_strength(xml_text: str) -> list[FxStrength]:
    root = ElementTree.fromstring(xml_text)
    series: dict[str, list[tuple[date, float]]] = {}
    for element in root.iter():
        day = element.attrib.get("time")
        if not day:
            continue
        observation_date = date.fromisoformat(day)
        for child in element:
            currency = child.attrib.get("currency")
            rate = child.attrib.get("rate")
            if currency and rate:
                series.setdefault(currency, []).append((observation_date, float(rate)))

    output: list[FxStrength] = []
    for currency in ("USD", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"):
        observations = sorted(series.get(currency, []), key=lambda item: item[0])
        if len(observations) < 2:
            continue
        values = [item[1] for item in observations]
        output.append(
            FxStrength(
                currency=currency,
                change_1d_pct=_change(values, 1),
                change_5d_pct=_change(values, 5),
                change_20d_pct=_change(values, 20),
                as_of=observations[-1][0],
            )
        )
    if not output:
        raise ValueError("ECB response contained no supported FX series")
    return output


def fetch_currency_strength() -> ProviderResult:
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.ecb.europa.eu"}),
        accepted_content_types=("text/xml", "application/xml"),
        max_bytes=2 * 1024 * 1024,
    )
    response = get_text(ECB_90D_URL, policy=policy)
    data = parse_ecb_strength(response.text)
    return ProviderResult(
        provider="ecb_fx_reference_rates",
        data=data,
        provenance=build_provenance(
            "ecb_fx_reference_rates",
            response.url,
            response.raw,
        ),
    )
