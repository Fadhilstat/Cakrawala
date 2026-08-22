from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cakrawala.personal.forex_analytics import ForexDeal
from cakrawala.personal.forex_review import (
    cumulative_equity_points,
    performance_by_hour_utc,
    performance_by_side,
    performance_by_symbol,
    performance_by_weekday,
    review_summary,
)


def _deal(
    ticket: str,
    symbol: str,
    side: str,
    pnl: float,
    closed_at: datetime,
    *,
    hold_minutes: int = 60,
) -> ForexDeal:
    return ForexDeal(
        ticket=ticket,
        account_name="primary",
        symbol=symbol,
        side=side,
        volume=0.1,
        entry_price=1.1,
        exit_price=1.2,
        opened_at=closed_at - timedelta(minutes=hold_minutes),
        closed_at=closed_at,
        realized_pnl=pnl,
        commission=0,
        swap=0,
    )


def test_review_summary_tracks_hold_time_and_streaks() -> None:
    deals = [
        _deal("1", "EURUSD", "BUY", 10, datetime(2026, 8, 3, 8, tzinfo=UTC)),
        _deal("2", "EURUSD", "BUY", 20, datetime(2026, 8, 4, 9, tzinfo=UTC)),
        _deal("3", "GBPUSD", "SELL", -5, datetime(2026, 8, 5, 10, tzinfo=UTC)),
        _deal("4", "GBPUSD", "SELL", -7, datetime(2026, 8, 6, 11, tzinfo=UTC)),
    ]

    summary = review_summary(deals)

    assert summary.average_hold_minutes == pytest.approx(60)
    assert summary.longest_win_streak == 2
    assert summary.longest_loss_streak == 2
    assert summary.current_streak == 2
    assert summary.current_streak_kind == "LOSS"
    assert summary.best_trade == pytest.approx(20)
    assert summary.worst_trade == pytest.approx(-7)


def test_grouped_review_views_use_closed_trade_net_pnl() -> None:
    deals = [
        _deal("1", "EURUSD", "BUY", 10, datetime(2026, 8, 3, 8, tzinfo=UTC)),
        _deal("2", "EURUSD", "SELL", -4, datetime(2026, 8, 3, 9, tzinfo=UTC)),
        _deal("3", "USDJPY", "BUY", 7, datetime(2026, 8, 4, 8, tzinfo=UTC)),
    ]

    symbols = {row.label: row for row in performance_by_symbol(deals)}
    sides = {row.label: row for row in performance_by_side(deals)}
    weekdays = {row.label: row for row in performance_by_weekday(deals)}
    hours = {row.label: row for row in performance_by_hour_utc(deals)}

    assert symbols["EURUSD"].net_pnl == pytest.approx(6)
    assert symbols["EURUSD"].win_rate_percent == pytest.approx(50)
    assert sides["BUY"].net_pnl == pytest.approx(17)
    assert weekdays["Monday"].trades == 2
    assert hours["08:00"].trades == 2


def test_cumulative_equity_points_are_chronological() -> None:
    first = datetime(2026, 8, 1, 8, tzinfo=UTC)
    second = datetime(2026, 8, 2, 8, tzinfo=UTC)
    deals = [
        _deal("2", "EURUSD", "BUY", -5, second),
        _deal("1", "EURUSD", "BUY", 20, first),
    ]

    points = cumulative_equity_points(deals)

    assert points[0] == (first, pytest.approx(20))
    assert points[1] == (second, pytest.approx(15))
