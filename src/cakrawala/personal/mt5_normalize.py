from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Iterable

DEAL_TYPE_BUY = 0
DEAL_TYPE_SELL = 1
DEAL_ENTRY_IN = 0
DEAL_ENTRY_OUT = 1
DEAL_ENTRY_INOUT = 2
DEAL_ENTRY_OUT_BY = 3


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _timestamp(seconds: Any) -> str:
    return datetime.fromtimestamp(float(seconds), tz=UTC).isoformat()


def normalize_account(account: Any, captured_at: datetime) -> dict[str, Any]:
    login = str(_value(account, "login", "account"))
    floating_pnl = float(_value(account, "profit", 0.0))
    margin_level = _value(account, "margin_level")
    return {
        "account_name": login,
        "balance": float(_value(account, "balance", 0.0)),
        "equity": float(_value(account, "equity", 0.0)),
        "floating_pnl": floating_pnl,
        "margin_level_percent": float(margin_level) if margin_level else None,
        "captured_at": captured_at.astimezone(UTC).isoformat(),
    }


def normalize_positions(
    positions: Iterable[Any],
    account_name: str,
    captured_at: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for position in positions:
        side_type = int(_value(position, "type", -1))
        if side_type not in {DEAL_TYPE_BUY, DEAL_TYPE_SELL}:
            continue
        rows.append(
            {
                "ticket": str(_value(position, "ticket")),
                "symbol": str(_value(position, "symbol", "")).upper(),
                "side": "BUY" if side_type == DEAL_TYPE_BUY else "SELL",
                "volume": float(_value(position, "volume", 0.0)),
                "entry_price": float(_value(position, "price_open", 0.0)),
                "current_price": float(_value(position, "price_current", 0.0)),
                "stop_loss": _positive_or_none(_value(position, "sl")),
                "take_profit": _positive_or_none(_value(position, "tp")),
                "floating_pnl": float(_value(position, "profit", 0.0)),
                "captured_at": captured_at.astimezone(UTC).isoformat(),
                "account_name": account_name,
            }
        )
    return rows


def _positive_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    number = float(value)
    return number if number > 0 else None


def _weighted_price(items: list[Any]) -> float:
    volume = sum(float(_value(item, "volume", 0.0)) for item in items)
    if volume <= 0:
        raise ValueError("weighted price requires positive volume")
    weighted = sum(
        float(_value(item, "price", 0.0)) * float(_value(item, "volume", 0.0))
        for item in items
    )
    return weighted / volume


def aggregate_closed_positions(
    deals: Iterable[Any],
    account_name: str,
    *,
    volume_tolerance: float = 1e-8,
) -> list[dict[str, Any]]:
    grouped: dict[int, list[Any]] = defaultdict(list)
    for deal in deals:
        position_id = int(_value(deal, "position_id", 0) or 0)
        if position_id > 0:
            grouped[position_id].append(deal)

    records: list[dict[str, Any]] = []
    for position_id, group in grouped.items():
        ordered = sorted(group, key=lambda item: float(_value(item, "time_msc", 0)))
        entry_codes = {int(_value(item, "entry", -1)) for item in ordered}
        if entry_codes & {DEAL_ENTRY_INOUT, DEAL_ENTRY_OUT_BY}:
            continue

        entries = [item for item in ordered if int(_value(item, "entry", -1)) == DEAL_ENTRY_IN]
        exits = [item for item in ordered if int(_value(item, "entry", -1)) == DEAL_ENTRY_OUT]
        if not entries or not exits:
            continue

        entry_types = {int(_value(item, "type", -1)) for item in entries}
        if len(entry_types) != 1 or not entry_types <= {DEAL_TYPE_BUY, DEAL_TYPE_SELL}:
            continue

        entry_volume = sum(float(_value(item, "volume", 0.0)) for item in entries)
        exit_volume = sum(float(_value(item, "volume", 0.0)) for item in exits)
        if entry_volume <= 0 or abs(entry_volume - exit_volume) > volume_tolerance:
            continue

        symbol = str(_value(entries[0], "symbol", "")).upper()
        if not symbol:
            continue
        side_type = next(iter(entry_types))
        opened_at = min(float(_value(item, "time", 0.0)) for item in entries)
        closed_at = max(float(_value(item, "time", 0.0)) for item in exits)

        records.append(
            {
                "ticket": str(position_id),
                "account_name": account_name,
                "symbol": symbol,
                "side": "BUY" if side_type == DEAL_TYPE_BUY else "SELL",
                "volume": entry_volume,
                "entry_price": _weighted_price(entries),
                "exit_price": _weighted_price(exits),
                "opened_at": _timestamp(opened_at),
                "closed_at": _timestamp(closed_at),
                "realized_pnl": sum(float(_value(item, "profit", 0.0)) for item in ordered),
                "commission": sum(float(_value(item, "commission", 0.0)) for item in ordered),
                "swap": sum(float(_value(item, "swap", 0.0)) for item in ordered),
                "fee": sum(float(_value(item, "fee", 0.0)) for item in ordered),
                "result_r": None,
            }
        )

    return sorted(records, key=lambda item: str(item["closed_at"]), reverse=True)
