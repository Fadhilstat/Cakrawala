from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isclose, isfinite


class SurpriseState(StrEnum):
    UPSIDE_SURPRISE = "UPSIDE_SURPRISE"
    DOWNSIDE_SURPRISE = "DOWNSIDE_SURPRISE"
    INLINE = "INLINE"
    NO_FORECAST = "NO_FORECAST"
    INVALID = "INVALID"


class IndicatorSemantics(StrEnum):
    INFLATION = "INFLATION"
    HIGHER_STRONGER = "HIGHER_STRONGER"
    LOWER_STRONGER = "LOWER_STRONGER"
    CENTRAL_BANK = "CENTRAL_BANK"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"


@dataclass(frozen=True)
class EconomicRelease:
    event: str
    currency: str
    actual: float | int | str | None
    forecast: float | int | str | None
    previous: float | int | str | None
    source: str = ""
    source_url: str = ""


@dataclass(frozen=True)
class EconomicSurpriseAssessment:
    event: str
    currency: str
    state: SurpriseState
    semantics: IndicatorSemantics
    actual: float | None
    forecast: float | None
    previous: float | None
    surprise: float | None
    previous_change: float | None
    interpretation: str
    policy_impulse: str
    reasons: tuple[str, ...]


_SUFFIXES = {
    "K": 1_000.0,
    "M": 1_000_000.0,
    "B": 1_000_000_000.0,
    "T": 1_000_000_000_000.0,
}


def parse_calendar_number(value: float | int | str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed if isfinite(parsed) else None

    text = str(value).strip().upper()
    if not text or text in {"N/A", "NA", "NULL", "NONE", "-"}:
        return None

    text = text.replace("\u2212", "-").replace(",", "").replace("%", "")
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([KMBT]?)", text)
    if match is None:
        return None

    number = float(match.group(1))
    multiplier = _SUFFIXES.get(match.group(2), 1.0)
    parsed = number * multiplier
    return parsed if isfinite(parsed) else None


def classify_indicator(event: str) -> IndicatorSemantics:
    normalized = " ".join(event.lower().replace("-", " ").split())

    inflation_terms = (
        "cpi",
        "consumer price",
        "pce",
        "personal consumption expenditure",
        "inflation",
        "ppi",
        "producer price",
    )
    if any(term in normalized for term in inflation_terms):
        return IndicatorSemantics.INFLATION

    lower_stronger_terms = (
        "unemployment rate",
        "jobless claims",
        "unemployment claims",
        "claimant count",
    )
    if any(term in normalized for term in lower_stronger_terms):
        return IndicatorSemantics.LOWER_STRONGER

    central_bank_terms = (
        "interest rate decision",
        "policy rate",
        "fed funds rate",
        "deposit facility rate",
        "refinancing rate",
        "cash rate",
        "bank rate",
    )
    if any(term in normalized for term in central_bank_terms):
        return IndicatorSemantics.CENTRAL_BANK

    higher_stronger_terms = (
        "nonfarm payroll",
        "non farm payroll",
        "payrolls",
        "employment change",
        "average hourly earnings",
        "wage growth",
        "retail sales",
        "gdp",
        "gross domestic product",
        "pmi",
        "industrial production",
        "manufacturing production",
        "consumer confidence",
        "business confidence",
    )
    if any(term in normalized for term in higher_stronger_terms):
        return IndicatorSemantics.HIGHER_STRONGER

    return IndicatorSemantics.CONTEXT_DEPENDENT


def _surprise_state(actual: float, forecast: float) -> SurpriseState:
    if isclose(actual, forecast, rel_tol=0.0025, abs_tol=1e-12):
        return SurpriseState.INLINE
    if actual > forecast:
        return SurpriseState.UPSIDE_SURPRISE
    return SurpriseState.DOWNSIDE_SURPRISE


def _interpretation(
    state: SurpriseState,
    semantics: IndicatorSemantics,
) -> tuple[str, str]:
    if state == SurpriseState.INLINE:
        return "roughly in line with consensus", "NEUTRAL"
    if state == SurpriseState.NO_FORECAST:
        return "no consensus comparison is available", "INSUFFICIENT"
    if state == SurpriseState.INVALID:
        return "the release values are not usable", "INSUFFICIENT"

    upside = state == SurpriseState.UPSIDE_SURPRISE
    if semantics == IndicatorSemantics.INFLATION:
        if upside:
            return "hotter than consensus", "HAWKISH_PRESSURE"
        return "cooler than consensus", "DOVISH_PRESSURE"

    if semantics == IndicatorSemantics.HIGHER_STRONGER:
        if upside:
            return "stronger than consensus", "GROWTH_POSITIVE"
        return "weaker than consensus", "GROWTH_NEGATIVE"

    if semantics == IndicatorSemantics.LOWER_STRONGER:
        if upside:
            return "weaker than consensus", "GROWTH_NEGATIVE"
        return "stronger than consensus", "GROWTH_POSITIVE"

    if semantics == IndicatorSemantics.CENTRAL_BANK:
        if upside:
            return "rate outcome above consensus", "HAWKISH_PRESSURE"
        return "rate outcome below consensus", "DOVISH_PRESSURE"

    if upside:
        return "numerically above consensus", "CONTEXT_REQUIRED"
    return "numerically below consensus", "CONTEXT_REQUIRED"


def assess_economic_release(release: EconomicRelease) -> EconomicSurpriseAssessment:
    event = " ".join(release.event.split())
    currency = release.currency.strip().upper()
    actual = parse_calendar_number(release.actual)
    forecast = parse_calendar_number(release.forecast)
    previous = parse_calendar_number(release.previous)
    semantics = classify_indicator(event)

    if not event or actual is None:
        state = SurpriseState.INVALID
        interpretation, impulse = _interpretation(state, semantics)
        return EconomicSurpriseAssessment(
            event=event,
            currency=currency,
            state=state,
            semantics=semantics,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=None,
            previous_change=None,
            interpretation=interpretation,
            policy_impulse=impulse,
            reasons=("A valid event name and actual value are required.",),
        )

    if forecast is None:
        state = SurpriseState.NO_FORECAST
        surprise = None
    else:
        state = _surprise_state(actual, forecast)
        surprise = actual - forecast

    previous_change = None if previous is None else actual - previous
    interpretation, impulse = _interpretation(state, semantics)

    reasons: list[str] = []
    if forecast is not None:
        reasons.append(
            f"Actual differs from consensus by {surprise:+.6g} in normalized units."
        )
    else:
        reasons.append("Consensus forecast is unavailable, so surprise cannot be scored.")
    if previous_change is not None:
        reasons.append(
            "Actual differs from the previous release by "
            f"{previous_change:+.6g} in normalized units."
        )
    if semantics == IndicatorSemantics.INFLATION:
        reasons.append(
            "Inflation surprise is policy-sensitive and is not a direct currency "
            "or equity signal."
        )
    elif semantics == IndicatorSemantics.CENTRAL_BANK:
        reasons.append(
            "Rate decisions require statement, guidance, and market-pricing context "
            "before a directional view."
        )
    elif semantics == IndicatorSemantics.CONTEXT_DEPENDENT:
        reasons.append(
            "The event has no safe generic higher-is-better rule and needs macro context."
        )

    return EconomicSurpriseAssessment(
        event=event,
        currency=currency,
        state=state,
        semantics=semantics,
        actual=actual,
        forecast=forecast,
        previous=previous,
        surprise=surprise,
        previous_change=previous_change,
        interpretation=interpretation,
        policy_impulse=impulse,
        reasons=tuple(reasons),
    )
