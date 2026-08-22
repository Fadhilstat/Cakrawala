from __future__ import annotations

from typing import Any

import psycopg

from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal


def _validate(database_url: str, owner_sub: str, limit: int) -> None:
    if not database_url:
        raise ValueError("database_url is required")
    if not owner_sub or len(owner_sub) > 255:
        raise ValueError("owner_sub is invalid")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")


def latest_account_snapshot(
    database_url: str,
    owner_sub: str,
    *,
    account_name: str | None = None,
) -> AccountSnapshot | None:
    _validate(database_url, owner_sub, 1)
    values: list[Any] = [owner_sub]
    account_filter = ""
    if account_name:
        account_filter = " AND account_name = %s"
        values.append(account_name)
    query = f"""
        SELECT account_name, balance, equity, floating_pnl,
               margin_level_percent, captured_at
        FROM forex_account_snapshots
        WHERE owner_sub = %s{account_filter}
        ORDER BY captured_at DESC
        LIMIT 1
    """
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, values)
        row = cursor.fetchone()
    if row is None:
        return None
    return AccountSnapshot(
        account_name=str(row[0]),
        balance=float(row[1]),
        equity=float(row[2]),
        floating_pnl=float(row[3]),
        margin_level_percent=float(row[4]) if row[4] is not None else None,
        captured_at=row[5],
    )


def list_forex_deals(
    database_url: str,
    owner_sub: str,
    *,
    account_name: str | None = None,
    limit: int = 250,
) -> list[ForexDeal]:
    _validate(database_url, owner_sub, limit)
    values: list[Any] = [owner_sub]
    account_filter = ""
    if account_name:
        account_filter = " AND account_name = %s"
        values.append(account_name)
    values.append(limit)
    query = f"""
        SELECT ticket, account_name, symbol, side, volume, entry_price,
               exit_price, opened_at, closed_at, realized_pnl, commission,
               swap, result_r
        FROM forex_deals
        WHERE owner_sub = %s{account_filter}
        ORDER BY COALESCE(closed_at, opened_at) DESC
        LIMIT %s
    """
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, values)
        rows = cursor.fetchall()
    return [
        ForexDeal(
            ticket=str(row[0]),
            account_name=str(row[1]),
            symbol=str(row[2]),
            side=str(row[3]),
            volume=float(row[4]),
            entry_price=float(row[5]),
            exit_price=float(row[6]) if row[6] is not None else None,
            opened_at=row[7],
            closed_at=row[8],
            realized_pnl=float(row[9]),
            commission=float(row[10]),
            swap=float(row[11]),
            result_r=float(row[12]) if row[12] is not None else None,
        )
        for row in rows
    ]
