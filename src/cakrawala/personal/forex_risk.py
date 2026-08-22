from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal, daily_pnl, performance_summary
from cakrawala.personal.forex_sync import PositionSnapshot


class ForexRiskState(StrEnum):
    NO_DATA = "NO DATA"
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    LOCKED = "LOCKED"


@dataclass(frozen=True)
class ForexRiskPolicy:
    daily_closed_loss_limit_percent: float
    floating_loss_limit_percent: float
    closed_deal_drawdown_limit_percent: float
    minimum_margin_level_percent: float
    maximum_open_positions: int
    maximum_positions_without_stop: int
    snapshot_stale_minutes: int


@dataclass(frozen=True)
class ForexRiskAssessment:
    state: ForexRiskState
    reasons: tuple[str, ...]
    daily_closed_pnl_percent: float | None
    floating_pnl_percent: float | None
    closed_deal_drawdown_percent: float | None
    positions_without_stop: int
    open_positions: int
    snapshot_age_minutes: float | None


def policy_from_mapping(values: dict[str, object]) -> ForexRiskPolicy:
    return ForexRiskPolicy(
        daily_closed_loss_limit_percent=float(values["daily_closed_loss_limit_percent"]),
        floating_loss_limit_percent=float(values["floating_loss_limit_percent"]),
        closed_deal_drawdown_limit_percent=float(values["closed_deal_drawdown_limit_percent"]),
        minimum_margin_level_percent=float(values["minimum_margin_level_percent"]),
        maximum_open_positions=int(values["maximum_open_positions"]),
        maximum_positions_without_stop=int(values["maximum_positions_without_stop"]),
        snapshot_stale_minutes=int(values["snapshot_stale_minutes"]),
    )


def assess_forex_risk(
    snapshot: AccountSnapshot | None,
    positions: list[PositionSnapshot],
    deals: list[ForexDeal],
    policy: ForexRiskPolicy,
    *,
    now: datetime | None = None,
) -> ForexRiskAssessment:
    if snapshot is None or snapshot.balance <= 0:
        return ForexRiskAssessment(
            state=ForexRiskState.NO_DATA,
            reasons=("current account snapshot is required",),
            daily_closed_pnl_percent=None,
            floating_pnl_percent=None,
            closed_deal_drawdown_percent=None,
            positions_without_stop=sum(item.stop_loss is None for item in positions),
            open_positions=len(positions),
            snapshot_age_minutes=None,
        )

    reference_time = now or datetime.now(UTC)
    if reference_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    snapshot_time = snapshot.captured_at.astimezone(UTC)
    age_minutes = max(
        (reference_time.astimezone(UTC) - snapshot_time).total_seconds() / 60,
        0.0,
    )

    today_pnl = daily_pnl(deals).get(reference_time.astimezone(UTC).date(), 0.0)
    daily_percent = today_pnl / snapshot.balance * 100
    floating_percent = snapshot.floating_pnl / snapshot.balance * 100
    drawdown = performance_summary(deals).max_drawdown
    drawdown_percent = drawdown / snapshot.balance * 100
    positions_without_stop = sum(item.stop_loss is None for item in positions)

    locked: list[str] = []
    caution: list[str] = []

    if daily_percent <= -abs(policy.daily_closed_loss_limit_percent):
        locked.append("daily closed loss limit reached")
    if floating_percent <= -abs(policy.floating_loss_limit_percent):
        locked.append("floating loss limit reached")
    if drawdown_percent >= abs(policy.closed_deal_drawdown_limit_percent):
        locked.append("closed-deal drawdown limit reached")
    if (
        snapshot.margin_level_percent is not None
        and snapshot.margin_level_percent < policy.minimum_margin_level_percent
    ):
        locked.append("margin level is below the configured minimum")

    if len(positions) > policy.maximum_open_positions:
        caution.append("open position count exceeds the configured maximum")
    if positions_without_stop > policy.maximum_positions_without_stop:
        caution.append("one or more open positions exceed the stop-loss policy")
    if age_minutes > policy.snapshot_stale_minutes:
        caution.append("account snapshot is stale")

    if locked:
        state = ForexRiskState.LOCKED
        reasons = tuple(locked + caution)
    elif caution:
        state = ForexRiskState.CAUTION
        reasons = tuple(caution)
    else:
        state = ForexRiskState.SAFE
        reasons = ("all configured personal risk checks passed",)

    return ForexRiskAssessment(
        state=state,
        reasons=reasons,
        daily_closed_pnl_percent=daily_percent,
        floating_pnl_percent=floating_percent,
        closed_deal_drawdown_percent=drawdown_percent,
        positions_without_stop=positions_without_stop,
        open_positions=len(positions),
        snapshot_age_minutes=age_minutes,
    )
