from datetime import UTC, datetime

import pytest

from cakrawala.data.providers.bls_calendar import parse_calendar
from cakrawala.intelligence.bias import BiasInput, assess_research_bias
from cakrawala.intelligence.risk import build_position_plan, expectancy_r, projected_equity
from cakrawala.intelligence.sessions import current_sessions


def test_position_size_uses_defined_account_risk() -> None:
    plan = build_position_plan(
        account_size=10_000,
        risk_percent=1,
        entry=100,
        stop=98,
        target=104,
    )
    assert plan.risk_amount == pytest.approx(100)
    assert plan.quantity == pytest.approx(50)
    assert plan.reward_risk == pytest.approx(2)


def test_position_plan_rejects_zero_stop_distance() -> None:
    with pytest.raises(ValueError):
        build_position_plan(
            account_size=10_000,
            risk_percent=1,
            entry=100,
            stop=100,
        )


def test_expectancy_and_curve_are_deterministic() -> None:
    expectancy = expectancy_r(
        win_rate_percent=50,
        average_win_r=2,
        average_loss_r=1,
    )
    assert expectancy == pytest.approx(0.5)
    curve = projected_equity(
        starting_equity=10_000,
        risk_percent=1,
        expectancy_per_trade_r=expectancy,
        trades=2,
    )
    assert curve == pytest.approx([10_000, 10_050, 10_100.25])


def test_bias_board_is_contrarian_when_crowd_is_extreme() -> None:
    assessment = assess_research_bias(
        BiasInput(
            momentum_30d_pct=8,
            drawdown_pct=-1,
            volatility_30d_pct=50,
            long_account=0.75,
            funding_rate=0.001,
            high_attention_news=0,
        )
    )
    assert assessment.label == "Neutral research bias"
    assert "crowd positioning is heavily long" in assessment.reasons


def test_market_sessions_are_timezone_aware() -> None:
    sessions = current_sessions(datetime(2026, 8, 21, 8, 0, tzinfo=UTC))
    assert {item.name for item in sessions} == {"Asia", "London", "New York"}
    assert all(isinstance(item.is_open, bool) for item in sessions)


def test_bls_calendar_parser_handles_folded_events() -> None:
    sample = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20260825T123000Z
SUMMARY:Consumer Price Index
URL:https://www.bls.gov/news.release/cpi.toc.htm
END:VEVENT
BEGIN:VEVENT
DTSTART:20260826T123000Z
SUMMARY:Employment Situation
END:VEVENT
END:VCALENDAR
"""
    events = parse_calendar(sample)
    assert [event.title for event in events] == [
        "Consumer Price Index",
        "Employment Situation",
    ]
    assert events[0].starts_at.tzinfo is UTC
    assert events[1].link == "https://www.bls.gov"
