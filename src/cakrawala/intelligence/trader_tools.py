from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropRiskBudget:
    daily_loss_budget: float
    total_loss_budget: float
    remaining_daily_buffer: float
    full_risk_losses_to_daily_cap: float


def pip_or_tick_value(
    *,
    units_per_lot: float,
    tick_size: float,
    lots: float,
    quote_to_account: float,
) -> float:
    values = (units_per_lot, tick_size, lots, quote_to_account)
    if any(value < 0 for value in values):
        raise ValueError("pip or tick inputs cannot be negative")
    if units_per_lot == 0 or tick_size == 0 or quote_to_account == 0:
        raise ValueError("units, tick size, and conversion must be positive")
    return units_per_lot * tick_size * lots * quote_to_account


def position_pnl(
    *,
    side: str,
    entry: float,
    exit_price: float,
    quantity: float,
) -> float:
    if side not in {"LONG", "SHORT"}:
        raise ValueError("side must be LONG or SHORT")
    if entry <= 0 or exit_price <= 0 or quantity < 0:
        raise ValueError("price must be positive and quantity cannot be negative")
    direction = 1 if side == "LONG" else -1
    return (exit_price - entry) * quantity * direction


def compound_projection(
    *,
    starting_capital: float,
    period_change_percent: float,
    periods: int,
) -> float:
    if starting_capital <= 0:
        raise ValueError("starting capital must be positive")
    if periods < 0:
        raise ValueError("periods cannot be negative")
    factor = 1 + period_change_percent / 100
    if factor < 0:
        raise ValueError("period change cannot reduce capital below zero in one step")
    return starting_capital * factor**periods


def prop_risk_budget(
    *,
    equity: float,
    daily_loss_limit_percent: float,
    total_loss_limit_percent: float,
    planned_risk_percent: float,
    current_daily_pnl: float = 0.0,
) -> PropRiskBudget:
    if equity <= 0:
        raise ValueError("equity must be positive")
    limits = (
        daily_loss_limit_percent,
        total_loss_limit_percent,
        planned_risk_percent,
    )
    if any(value <= 0 for value in limits):
        raise ValueError("risk limits must be positive")

    daily_budget = equity * daily_loss_limit_percent / 100
    total_budget = equity * total_loss_limit_percent / 100
    remaining = max(daily_budget + current_daily_pnl, 0.0)
    full_risk_amount = equity * planned_risk_percent / 100
    losses_to_cap = remaining / full_risk_amount
    return PropRiskBudget(
        daily_loss_budget=daily_budget,
        total_loss_budget=total_budget,
        remaining_daily_buffer=remaining,
        full_risk_losses_to_daily_cap=losses_to_cap,
    )
