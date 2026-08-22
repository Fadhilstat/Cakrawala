from datetime import UTC, datetime

import pytest

from cakrawala.personal.forex_analytics import (
    AccountSnapshot,
    ForexDeal,
    daily_pnl,
    performance_summary,
    pnl_by_symbol,
)


def _deal(
    ticket: str,
    symbol: str,
    pnl: float,
    closed_at: datetime,
    *,
    commission: float = 0.0,
    swap: float = 0.0,
    result_r: float | None = None,
) -> ForexDeal:
    return ForexDeal(
        ticket=ticket,
        account_name="demo",
        symbol=symbol,
        side="BUY",
        volume=0.1,
        entry_price=1.1,
        exit_price=1.2,
        opened_at=datetime(2026, 8, 1, tzinfo=UTC),
        closed_at=closed_at,
        realized_pnl=pnl,
        commission=commission,
        swap=swap,
        result_r=result_r,
    )


def test_performance_summary_uses_net_pnl_and_chronological_drawdown() -> None:
    deals = [
        _deal("3", "EURUSD", 40, datetime(2026, 8, 3, tzinfo=UTC), result_r=0.8),
        _deal("1", "EURUSD", 100, datetime(2026, 8, 1, tzinfo=UTC), commission=-2, result_r=2),
        _deal("2", "GBPUSD", -60, datetime(2026, 8, 2, tzinfo=UTC), swap=-1, result_r=-1),
    ]

    summary = performance_summary(deals)

    assert summary.net_pnl == pytest.approx(77)
    assert summary.gross_profit == pytest.approx(138)
    assert summary.gross_loss == pytest.approx(-61)
    assert summary.win_rate_percent == pytest.approx(200 / 3)
    assert summary.profit_factor == pytest.approx(138 / 61)
    assert summary.expectancy == pytest.approx(77 / 3)
    assert summary.average_r == pytest.approx(0.6)
    assert summary.max_drawdown == pytest.approx(61)
    assert summary.total_closed == 3


def test_daily_and_symbol_pnl_aggregate_without_duplicates() -> None:
    deals = [
        _deal("1", "EURUSD", 50, datetime(2026, 8, 2, 8, tzinfo=UTC)),
        _deal("2", "EURUSD", -20, datetime(2026, 8, 2, 12, tzinfo=UTC)),
        _deal("3", "USDJPY", 10, datetime(2026, 8, 3, tzinfo=UTC)),
    ]

    daily = daily_pnl(deals)
    symbols = pnl_by_symbol(deals)

    assert daily[datetime(2026, 8, 2, tzinfo=UTC).date()] == pytest.approx(30)
    assert daily[datetime(2026, 8, 3, tzinfo=UTC).date()] == pytest.approx(10)
    assert symbols == {"EURUSD": pytest.approx(30), "USDJPY": pytest.approx(10)}


def test_account_snapshot_keeps_private_broker_state_explicit() -> None:
    snapshot = AccountSnapshot(
        account_name="primary",
        balance=10_000,
        equity=10_125,
        floating_pnl=125,
        margin_level_percent=720,
        captured_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    assert snapshot.equity - snapshot.balance == pytest.approx(snapshot.floating_pnl)
