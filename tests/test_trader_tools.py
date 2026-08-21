import pytest

from cakrawala.intelligence.trader_tools import (
    compound_projection,
    pip_or_tick_value,
    position_pnl,
    prop_risk_budget,
)


def test_pip_or_tick_value_uses_explicit_contract_inputs() -> None:
    value = pip_or_tick_value(
        units_per_lot=100000,
        tick_size=0.0001,
        lots=0.1,
        quote_to_account=1.0,
    )
    assert value == pytest.approx(1.0)


def test_position_pnl_respects_direction() -> None:
    assert position_pnl(side="LONG", entry=100, exit_price=102, quantity=2) == 4
    assert position_pnl(side="SHORT", entry=100, exit_price=98, quantity=2) == 4


def test_compound_projection_is_deterministic() -> None:
    value = compound_projection(
        starting_capital=1000,
        period_change_percent=10,
        periods=2,
    )
    assert value == pytest.approx(1210)


def test_prop_risk_budget_tracks_remaining_daily_buffer() -> None:
    budget = prop_risk_budget(
        equity=100000,
        daily_loss_limit_percent=5,
        total_loss_limit_percent=10,
        planned_risk_percent=1,
        current_daily_pnl=-2000,
    )
    assert budget.daily_loss_budget == pytest.approx(5000)
    assert budget.remaining_daily_buffer == pytest.approx(3000)
    assert budget.full_risk_losses_to_daily_cap == pytest.approx(3)
