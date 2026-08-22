from __future__ import annotations

from cakrawala.intelligence.economic_surprise import (
    EconomicRelease,
    IndicatorSemantics,
    SurpriseState,
    assess_economic_release,
    classify_indicator,
    parse_calendar_number,
)


def test_parse_calendar_number_handles_percent_and_suffixes() -> None:
    assert parse_calendar_number("3.2%") == 3.2
    assert parse_calendar_number("175K") == 175_000.0
    assert parse_calendar_number("-2.5M") == -2_500_000.0
    assert parse_calendar_number("N/A") is None


def test_nfp_upside_surprise_is_growth_positive() -> None:
    result = assess_economic_release(
        EconomicRelease(
            event="Nonfarm Payrolls",
            currency="USD",
            actual="210K",
            forecast="180K",
            previous="165K",
        )
    )
    assert result.state == SurpriseState.UPSIDE_SURPRISE
    assert result.semantics == IndicatorSemantics.HIGHER_STRONGER
    assert result.policy_impulse == "GROWTH_POSITIVE"
    assert result.surprise == 30_000.0


def test_unemployment_upside_surprise_is_growth_negative() -> None:
    result = assess_economic_release(
        EconomicRelease(
            event="Unemployment Rate",
            currency="USD",
            actual="4.4%",
            forecast="4.2%",
            previous="4.1%",
        )
    )
    assert result.state == SurpriseState.UPSIDE_SURPRISE
    assert result.semantics == IndicatorSemantics.LOWER_STRONGER
    assert result.policy_impulse == "GROWTH_NEGATIVE"


def test_cpi_upside_surprise_is_hawkish_pressure_not_trade_signal() -> None:
    result = assess_economic_release(
        EconomicRelease(
            event="Core CPI MoM",
            currency="USD",
            actual="0.4%",
            forecast="0.3%",
            previous="0.2%",
        )
    )
    assert result.state == SurpriseState.UPSIDE_SURPRISE
    assert result.semantics == IndicatorSemantics.INFLATION
    assert result.policy_impulse == "HAWKISH_PRESSURE"
    assert "not a direct currency or equity signal" in result.reasons[-1]


def test_missing_forecast_does_not_force_directional_surprise() -> None:
    result = assess_economic_release(
        EconomicRelease(
            event="Retail Sales MoM",
            currency="GBP",
            actual="0.6%",
            forecast=None,
            previous="0.1%",
        )
    )
    assert result.state == SurpriseState.NO_FORECAST
    assert result.surprise is None
    assert result.previous_change == 0.5


def test_unknown_indicator_requires_context() -> None:
    assert classify_indicator("Custom Sentiment Gauge") == IndicatorSemantics.CONTEXT_DEPENDENT
