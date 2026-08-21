from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionPlan:
    account_size: float
    risk_percent: float
    risk_amount: float
    entry: float
    stop: float
    target: float | None
    stop_distance: float
    quantity: float
    reward_risk: float | None


def build_position_plan(
    *,
    account_size: float,
    risk_percent: float,
    entry: float,
    stop: float,
    target: float | None = None,
) -> PositionPlan:
    if account_size <= 0:
        raise ValueError("account_size must be positive")
    if not 0 < risk_percent <= 10:
        raise ValueError("risk_percent must be between 0 and 10")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be positive")
    if target is not None and target <= 0:
        raise ValueError("target must be positive")

    stop_distance = abs(entry - stop)
    if stop_distance == 0:
        raise ValueError("entry and stop must differ")

    risk_amount = account_size * (risk_percent / 100)
    quantity = risk_amount / stop_distance
    reward_risk = None
    if target is not None:
        reward_distance = abs(target - entry)
        reward_risk = reward_distance / stop_distance

    return PositionPlan(
        account_size=account_size,
        risk_percent=risk_percent,
        risk_amount=risk_amount,
        entry=entry,
        stop=stop,
        target=target,
        stop_distance=stop_distance,
        quantity=quantity,
        reward_risk=reward_risk,
    )


def expectancy_r(
    *,
    win_rate_percent: float,
    average_win_r: float,
    average_loss_r: float,
) -> float:
    if not 0 <= win_rate_percent <= 100:
        raise ValueError("win_rate_percent must be between 0 and 100")
    if average_win_r < 0 or average_loss_r < 0:
        raise ValueError("average R values must be non-negative")
    win_rate = win_rate_percent / 100
    loss_rate = 1 - win_rate
    return win_rate * average_win_r - loss_rate * average_loss_r


def projected_equity(
    *,
    starting_equity: float,
    risk_percent: float,
    expectancy_per_trade_r: float,
    trades: int,
) -> list[float]:
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")
    if not 0 <= risk_percent <= 10:
        raise ValueError("risk_percent must be between 0 and 10")
    if not 0 <= trades <= 1000:
        raise ValueError("trades must be between 0 and 1000")

    equity = starting_equity
    curve = [equity]
    for _ in range(trades):
        expected_change = equity * (risk_percent / 100) * expectancy_per_trade_r
        equity += expected_change
        curve.append(equity)
    return curve
