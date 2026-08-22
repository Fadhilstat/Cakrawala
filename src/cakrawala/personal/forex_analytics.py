from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from math import sqrt
from statistics import mean, pstdev


@dataclass(frozen=True)
class ForexDeal:
    ticket: str
    account_name: str
    symbol: str
    side: str
    volume: float
    entry_price: float
    exit_price: float | None
    opened_at: datetime
    closed_at: datetime | None
    realized_pnl: float
    commission: float
    swap: float
    fee: float = 0.0
    result_r: float | None = None

    @property
    def net_pnl(self) -> float:
        return self.realized_pnl + self.commission + self.swap + self.fee

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None


@dataclass(frozen=True)
class AccountSnapshot:
    account_name: str
    balance: float
    equity: float
    floating_pnl: float
    margin_level_percent: float | None
    captured_at: datetime


@dataclass(frozen=True)
class ForexPerformance:
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate_percent: float | None
    profit_factor: float | None
    expectancy: float | None
    average_r: float | None
    max_drawdown: float
    sharpe_like: float | None
    total_closed: int
    winners: int
    losers: int


def performance_summary(deals: list[ForexDeal]) -> ForexPerformance:
    closed = sorted(
        (deal for deal in deals if deal.closed_at is not None),
        key=lambda deal: deal.closed_at,
    )
    pnls = [deal.net_pnl for deal in closed]
    winners = [value for value in pnls if value > 0]
    losers = [value for value in pnls if value < 0]
    gross_profit = sum(winners)
    gross_loss = sum(losers)
    total = len(closed)

    win_rate = (len(winners) / total * 100) if total else None
    profit_factor = None
    if gross_loss < 0:
        profit_factor = gross_profit / abs(gross_loss)

    expectancy = mean(pnls) if pnls else None
    r_values = [deal.result_r for deal in closed if deal.result_r is not None]
    average_r = mean(r_values) if r_values else None

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    sharpe_like = None
    if len(pnls) >= 2:
        volatility = pstdev(pnls)
        if volatility > 0:
            sharpe_like = mean(pnls) / volatility * sqrt(len(pnls))

    return ForexPerformance(
        net_pnl=sum(pnls),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        win_rate_percent=win_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
        average_r=average_r,
        max_drawdown=max_drawdown,
        sharpe_like=sharpe_like,
        total_closed=total,
        winners=len(winners),
        losers=len(losers),
    )


def daily_pnl(deals: list[ForexDeal]) -> dict[date, float]:
    totals: dict[date, float] = defaultdict(float)
    for deal in deals:
        if deal.closed_at is None:
            continue
        totals[deal.closed_at.date()] += deal.net_pnl
    return dict(sorted(totals.items()))


def pnl_by_symbol(deals: list[ForexDeal]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for deal in deals:
        if deal.closed_at is None:
            continue
        totals[deal.symbol.upper()] += deal.net_pnl
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))
