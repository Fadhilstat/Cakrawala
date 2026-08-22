from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import mean

from cakrawala.personal.forex_analytics import ForexDeal

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class ReviewSummary:
    average_hold_minutes: float | None
    longest_win_streak: int
    longest_loss_streak: int
    current_streak: int
    current_streak_kind: str
    best_trade: float | None
    worst_trade: float | None


@dataclass(frozen=True)
class GroupPerformance:
    label: str
    trades: int
    net_pnl: float
    win_rate_percent: float | None
    average_pnl: float


def _closed(deals: list[ForexDeal]) -> list[ForexDeal]:
    return sorted(
        (deal for deal in deals if deal.closed_at is not None),
        key=lambda deal: deal.closed_at,
    )


def cumulative_equity_points(deals: list[ForexDeal]) -> list[tuple[datetime, float]]:
    equity = 0.0
    points: list[tuple[datetime, float]] = []
    for deal in _closed(deals):
        assert deal.closed_at is not None
        equity += deal.net_pnl
        points.append((deal.closed_at, equity))
    return points


def review_summary(deals: list[ForexDeal]) -> ReviewSummary:
    closed = _closed(deals)
    holds = [
        (deal.closed_at - deal.opened_at).total_seconds() / 60
        for deal in closed
        if deal.closed_at is not None and deal.closed_at >= deal.opened_at
    ]
    pnls = [deal.net_pnl for deal in closed]

    longest_win = 0
    longest_loss = 0
    running_kind = "NONE"
    running_length = 0
    for pnl in pnls:
        kind = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"
        if kind == running_kind and kind != "FLAT":
            running_length += 1
        elif kind == "FLAT":
            running_kind = "NONE"
            running_length = 0
        else:
            running_kind = kind
            running_length = 1
        if running_kind == "WIN":
            longest_win = max(longest_win, running_length)
        elif running_kind == "LOSS":
            longest_loss = max(longest_loss, running_length)

    current_kind = "NONE"
    current_streak = 0
    for pnl in reversed(pnls):
        kind = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"
        if kind == "FLAT":
            break
        if current_kind == "NONE":
            current_kind = kind
        if kind != current_kind:
            break
        current_streak += 1

    return ReviewSummary(
        average_hold_minutes=mean(holds) if holds else None,
        longest_win_streak=longest_win,
        longest_loss_streak=longest_loss,
        current_streak=current_streak,
        current_streak_kind=current_kind,
        best_trade=max(pnls) if pnls else None,
        worst_trade=min(pnls) if pnls else None,
    )


def _group_performance(
    deals: list[ForexDeal],
    key_fn: object,
) -> list[GroupPerformance]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for deal in _closed(deals):
        label = str(key_fn(deal))  # type: ignore[operator]
        grouped[label].append(deal.net_pnl)

    rows: list[GroupPerformance] = []
    for label, pnls in grouped.items():
        wins = sum(value > 0 for value in pnls)
        rows.append(
            GroupPerformance(
                label=label,
                trades=len(pnls),
                net_pnl=sum(pnls),
                win_rate_percent=wins / len(pnls) * 100 if pnls else None,
                average_pnl=mean(pnls),
            )
        )
    return rows


def performance_by_symbol(deals: list[ForexDeal]) -> list[GroupPerformance]:
    return sorted(
        _group_performance(deals, lambda deal: deal.symbol.upper()),
        key=lambda item: item.net_pnl,
        reverse=True,
    )


def performance_by_weekday(deals: list[ForexDeal]) -> list[GroupPerformance]:
    rows = _group_performance(
        deals,
        lambda deal: WEEKDAYS[deal.closed_at.weekday()],
    )
    order = {name: index for index, name in enumerate(WEEKDAYS)}
    return sorted(rows, key=lambda item: order.get(item.label, 99))


def performance_by_hour_utc(deals: list[ForexDeal]) -> list[GroupPerformance]:
    return sorted(
        _group_performance(
            deals,
            lambda deal: f"{deal.closed_at.hour:02d}:00",
        ),
        key=lambda item: item.label,
    )


def performance_by_side(deals: list[ForexDeal]) -> list[GroupPerformance]:
    return sorted(
        _group_performance(deals, lambda deal: deal.side.upper()),
        key=lambda item: item.label,
    )
