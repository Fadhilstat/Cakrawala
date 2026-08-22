from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal
from cakrawala.personal.forex_risk import ForexRiskPolicy, ForexRiskState, assess_forex_risk
from cakrawala.personal.forex_sync import PositionSnapshot

POLICY = ForexRiskPolicy(
    daily_closed_loss_limit_percent=3,
    floating_loss_limit_percent=2,
    closed_deal_drawdown_limit_percent=8,
    minimum_margin_level_percent=150,
    maximum_open_positions=5,
    maximum_positions_without_stop=0,
    snapshot_stale_minutes=15,
)


def _snapshot(
    now: datetime,
    *,
    floating: float = 0,
    margin: float = 500,
) -> AccountSnapshot:
    return AccountSnapshot(
        account_name="primary",
        balance=10000,
        equity=10000 + floating,
        floating_pnl=floating,
        margin_level_percent=margin,
        captured_at=now,
    )


def _position(
    now: datetime,
    *,
    stop_loss: float | None = 1.09,
) -> PositionSnapshot:
    return PositionSnapshot(
        ticket="1",
        account_name="primary",
        symbol="EURUSD",
        side="BUY",
        volume=0.1,
        entry_price=1.1,
        current_price=1.11,
        stop_loss=stop_loss,
        take_profit=1.12,
        floating_pnl=10,
        captured_at=now,
    )


def _deal(now: datetime, pnl: float) -> ForexDeal:
    return ForexDeal(
        ticket=str(abs(hash((now, pnl)))),
        account_name="primary",
        symbol="EURUSD",
        side="BUY",
        volume=0.1,
        entry_price=1.1,
        exit_price=1.11,
        opened_at=now - timedelta(hours=1),
        closed_at=now,
        realized_pnl=pnl,
        commission=0,
        swap=0,
    )


def test_risk_guard_requires_account_snapshot() -> None:
    assessment = assess_forex_risk(None, [], [], POLICY)
    assert assessment.state == ForexRiskState.NO_DATA
    assert assessment.daily_closed_pnl_percent is None


def test_risk_guard_is_safe_when_policy_checks_pass() -> None:
    now = datetime(2026, 8, 22, 10, tzinfo=UTC)
    assessment = assess_forex_risk(
        _snapshot(now),
        [_position(now)],
        [_deal(now, 50)],
        POLICY,
        now=now,
    )
    assert assessment.state == ForexRiskState.SAFE
    assert assessment.positions_without_stop == 0
    assert assessment.snapshot_age_minutes == pytest.approx(0)


def test_risk_guard_locks_on_daily_loss_and_low_margin() -> None:
    now = datetime(2026, 8, 22, 10, tzinfo=UTC)
    assessment = assess_forex_risk(
        _snapshot(now, margin=100),
        [_position(now)],
        [_deal(now, -350)],
        POLICY,
        now=now,
    )
    assert assessment.state == ForexRiskState.LOCKED
    assert assessment.daily_closed_pnl_percent == pytest.approx(-3.5)
    assert "daily closed loss limit reached" in assessment.reasons
    assert "margin level is below the configured minimum" in assessment.reasons


def test_risk_guard_warns_on_stale_snapshot_and_missing_stop() -> None:
    now = datetime(2026, 8, 22, 10, tzinfo=UTC)
    old = now - timedelta(minutes=30)
    assessment = assess_forex_risk(
        _snapshot(old),
        [_position(old, stop_loss=None)],
        [],
        POLICY,
        now=now,
    )
    assert assessment.state == ForexRiskState.CAUTION
    assert assessment.positions_without_stop == 1
    assert assessment.snapshot_age_minutes == pytest.approx(30)


def test_risk_guard_uses_configured_daily_timezone() -> None:
    now = datetime(2026, 8, 22, 0, 30, tzinfo=UTC)
    prior_utc_day_but_same_wib_day = datetime(2026, 8, 21, 18, 30, tzinfo=UTC)
    assessment = assess_forex_risk(
        _snapshot(now),
        [],
        [_deal(prior_utc_day_but_same_wib_day, -350)],
        POLICY,
        now=now,
        timezone_name="Asia/Jakarta",
    )
    assert assessment.state == ForexRiskState.LOCKED
    assert assessment.daily_closed_pnl_percent == pytest.approx(-3.5)
