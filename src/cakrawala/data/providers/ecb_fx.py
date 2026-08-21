from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from xml.etree import ElementTree

from cakrawala.data.http import HttpPolicy, get_text
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult

ECB_90D_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
SUPPORTED_PAIRS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
    "EURJPY",
    "GBPJPY",
    "EURGBP",
)


@dataclass(frozen=True)
class FxStrength:
    currency: str
    change_1d_pct: float | None
    change_5d_pct: float | None
    change_20d_pct: float | None
    as_of: date


@dataclass(frozen=True)
class FxPairSnapshot:
    pair: str
    rate: float
    change_1d_pct: float | None
    change_5d_pct: float | None
    change_20d_pct: float | None
    as_of: date


def _parse_series(xml_text: str) -> dict[str, list[tuple[date, float]]]:
    root = ElementTree.fromstring(xml_text)
    series: dict[str, list[tuple[date, float]]] = {}
    observed_dates: set[date] = set()
    for element in root.iter():
        day = element.attrib.get("time")
        if not day:
            continue
        observation_date = date.fromisoformat(day)
        observed_dates.add(observation_date)
        for child in element:
            currency = child.attrib.get("currency")
            rate = child.attrib.get("rate")
            if currency and rate:
                series.setdefault(currency, []).append((observation_date, float(rate)))

    if observed_dates:
        series["EUR"] = [(day, 1.0) for day in sorted(observed_dates)]
    return series


def _change(values: list[float], periods: int, *, invert: bool = False) -> float | None:
    if len(values) <= periods:
        return None
    latest = values[-1]
    previous = values[-1 - periods]
    if previous == 0:
        return None
    change = ((latest / previous) - 1.0) * 100
    return -change if invert else change


def parse_ecb_strength(xml_text: str) -> list[FxStrength]:
    series = _parse_series(xml_text)
    output: list[FxStrength] = []
    for currency in ("USD", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"):
        observations = sorted(series.get(currency, []), key=lambda item: item[0])
        if len(observations) < 2:
            continue
        values = [item[1] for item in observations]
        output.append(
            FxStrength(
                currency=currency,
                change_1d_pct=_change(values, 1, invert=True),
                change_5d_pct=_change(values, 5, invert=True),
                change_20d_pct=_change(values, 20, invert=True),
                as_of=observations[-1][0],
            )
        )
    if not output:
        raise ValueError("ECB response contained no supported FX series")
    return output


def _pair_history(
    series: dict[str, list[tuple[date, float]]],
    pair: str,
) -> list[tuple[date, float]]:
    base = pair[:3]
    quote = pair[3:]
    base_by_date = dict(series.get(base, []))
    quote_by_date = dict(series.get(quote, []))
    shared_dates = sorted(set(base_by_date).intersection(quote_by_date))
    output: list[tuple[date, float]] = []
    for day in shared_dates:
        base_rate = base_by_date[day]
        quote_rate = quote_by_date[day]
        if base_rate <= 0 or quote_rate <= 0:
            continue
        output.append((day, quote_rate / base_rate))
    return output


def parse_ecb_pairs(xml_text: str) -> list[FxPairSnapshot]:
    series = _parse_series(xml_text)
    output: list[FxPairSnapshot] = []
    for pair in SUPPORTED_PAIRS:
        observations = _pair_history(series, pair)
        if len(observations) < 2:
            continue
        values = [item[1] for item in observations]
        output.append(
            FxPairSnapshot(
                pair=pair,
                rate=values[-1],
                change_1d_pct=_change(values, 1),
                change_5d_pct=_change(values, 5),
                change_20d_pct=_change(values, 20),
                as_of=observations[-1][0],
            )
        )
    if not output:
        raise ValueError("ECB response contained no supported FX pair history")
    return output


def _fetch_ecb_xml() -> tuple[str, bytes, str]:
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.ecb.europa.eu"}),
        accepted_content_types=("text/xml", "application/xml"),
        max_bytes=2 * 1024 * 1024,
    )
    response = get_text(ECB_90D_URL, policy=policy)
    return response.text, response.raw, response.url


def fetch_currency_strength() -> ProviderResult:
    text, raw, url = _fetch_ecb_xml()
    data = parse_ecb_strength(text)
    return ProviderResult(
        provider="ecb_fx_reference_rates",
        data=data,
        provenance=build_provenance("ecb_fx_reference_rates", url, raw),
    )


def fetch_forex_pairs() -> ProviderResult:
    text, raw, url = _fetch_ecb_xml()
    data = parse_ecb_pairs(text)
    return ProviderResult(
        provider="ecb_fx_reference_rates",
        data=data,
        provenance=build_provenance("ecb_fx_reference_rates", url, raw),
    )
