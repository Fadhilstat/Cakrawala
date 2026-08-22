from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal

MAX_POSITIONS = 200
MAX_DEALS = 2000


@dataclass(frozen=True)
class PositionSnapshot:
    ticket: str
    account_name: str
    symbol: str
    side: str
    volume: float
    entry_price: float
    current_price: float
    stop_loss: float | None
    take_profit: float | None
    floating_pnl: float
    captured_at: datetime


@dataclass(frozen=True)
class ForexSyncPayload:
    account: AccountSnapshot
    positions: list[PositionSnapshot]
    deals: list[ForexDeal]
    captured_at: datetime
    source: str
    payload_hash: str


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _text(value: Any, field: str, *, max_length: int = 100) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_length:
        raise ValueError(f"{field} is invalid")
    return cleaned


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if positive and number <= 0:
        raise ValueError(f"{field} must be positive")
    return number


def _optional_number(value: Any, field: str, *, positive: bool = False) -> float | None:
    if value is None or value == "":
        return None
    return _number(value, field, positive=positive)


def _side(value: Any, field: str = "side") -> str:
    side = _text(value, field, max_length=8).upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError(f"{field} must be BUY or SELL")
    return side


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def parse_sync_payload(payload: Any) -> ForexSyncPayload:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    account_raw = payload.get("account")
    positions_raw = payload.get("positions", [])
    deals_raw = payload.get("deals", [])
    source = _text(payload.get("source", "manual_or_bridge"), "source", max_length=60)
    captured_at = _timestamp(payload.get("captured_at"), "captured_at")

    if not isinstance(account_raw, dict):
        raise ValueError("account must be an object")
    if not isinstance(positions_raw, list) or len(positions_raw) > MAX_POSITIONS:
        raise ValueError("positions must be a bounded list")
    if not isinstance(deals_raw, list) or len(deals_raw) > MAX_DEALS:
        raise ValueError("deals must be a bounded list")

    account_name = _text(account_raw.get("account_name"), "account.account_name")
    account = AccountSnapshot(
        account_name=account_name,
        balance=_number(account_raw.get("balance"), "account.balance"),
        equity=_number(account_raw.get("equity"), "account.equity"),
        floating_pnl=_number(account_raw.get("floating_pnl"), "account.floating_pnl"),
        margin_level_percent=_optional_number(
            account_raw.get("margin_level_percent"),
            "account.margin_level_percent",
            positive=True,
        ),
        captured_at=_timestamp(
            account_raw.get("captured_at", payload.get("captured_at")),
            "account.captured_at",
        ),
    )

    positions: list[PositionSnapshot] = []
    position_keys: set[str] = set()
    for index, raw in enumerate(positions_raw):
        if not isinstance(raw, dict):
            raise ValueError(f"positions[{index}] must be an object")
        ticket = _text(raw.get("ticket"), f"positions[{index}].ticket")
        if ticket in position_keys:
            raise ValueError("duplicate position ticket in payload")
        position_keys.add(ticket)
        positions.append(
            PositionSnapshot(
                ticket=ticket,
                account_name=account_name,
                symbol=_text(raw.get("symbol"), f"positions[{index}].symbol").upper(),
                side=_side(raw.get("side"), f"positions[{index}].side"),
                volume=_number(raw.get("volume"), f"positions[{index}].volume", positive=True),
                entry_price=_number(
                    raw.get("entry_price"),
                    f"positions[{index}].entry_price",
                    positive=True,
                ),
                current_price=_number(
                    raw.get("current_price"),
                    f"positions[{index}].current_price",
                    positive=True,
                ),
                stop_loss=_optional_number(
                    raw.get("stop_loss"),
                    f"positions[{index}].stop_loss",
                    positive=True,
                ),
                take_profit=_optional_number(
                    raw.get("take_profit"),
                    f"positions[{index}].take_profit",
                    positive=True,
                ),
                floating_pnl=_number(
                    raw.get("floating_pnl"),
                    f"positions[{index}].floating_pnl",
                ),
                captured_at=_timestamp(
                    raw.get("captured_at", payload.get("captured_at")),
                    f"positions[{index}].captured_at",
                ),
            )
        )

    deals: list[ForexDeal] = []
    deal_keys: set[str] = set()
    for index, raw in enumerate(deals_raw):
        if not isinstance(raw, dict):
            raise ValueError(f"deals[{index}] must be an object")
        ticket = _text(raw.get("ticket"), f"deals[{index}].ticket")
        if ticket in deal_keys:
            raise ValueError("duplicate deal ticket in payload")
        deal_keys.add(ticket)
        opened_at = _timestamp(raw.get("opened_at"), f"deals[{index}].opened_at")
        closed_at_raw = raw.get("closed_at")
        closed_at = (
            _timestamp(closed_at_raw, f"deals[{index}].closed_at")
            if closed_at_raw
            else None
        )
        if closed_at is not None and closed_at < opened_at:
            raise ValueError("deal closed_at cannot be earlier than opened_at")
        deals.append(
            ForexDeal(
                ticket=ticket,
                account_name=account_name,
                symbol=_text(raw.get("symbol"), f"deals[{index}].symbol").upper(),
                side=_side(raw.get("side"), f"deals[{index}].side"),
                volume=_number(raw.get("volume"), f"deals[{index}].volume", positive=True),
                entry_price=_number(
                    raw.get("entry_price"),
                    f"deals[{index}].entry_price",
                    positive=True,
                ),
                exit_price=_optional_number(
                    raw.get("exit_price"),
                    f"deals[{index}].exit_price",
                    positive=True,
                ),
                opened_at=opened_at,
                closed_at=closed_at,
                realized_pnl=_number(raw.get("realized_pnl", 0), f"deals[{index}].realized_pnl"),
                commission=_number(raw.get("commission", 0), f"deals[{index}].commission"),
                swap=_number(raw.get("swap", 0), f"deals[{index}].swap"),
                result_r=_optional_number(raw.get("result_r"), f"deals[{index}].result_r"),
            )
        )

    return ForexSyncPayload(
        account=account,
        positions=positions,
        deals=deals,
        captured_at=captured_at,
        source=source,
        payload_hash=canonical_payload_hash(payload),
    )
