from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg

from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal
from cakrawala.personal.forex_sync import ForexSyncPayload, PositionSnapshot


@dataclass(frozen=True)
class SyncIngestResult:
    duplicate_batch: bool
    inserted_positions: int
    inserted_deals: int


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
               swap, fee, result_r
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
            fee=float(row[12]),
            result_r=float(row[13]) if row[13] is not None else None,
        )
        for row in rows
    ]


def latest_position_snapshots(
    database_url: str,
    owner_sub: str,
    *,
    account_name: str | None = None,
    limit: int = 200,
) -> list[PositionSnapshot]:
    _validate(database_url, owner_sub, limit)
    account_filter = ""
    account_values: list[Any] = []
    if account_name:
        account_filter = " AND account_name = %s"
        account_values.append(account_name)
    query = f"""
        WITH latest AS (
            SELECT MAX(captured_at) AS captured_at
            FROM forex_position_snapshots
            WHERE owner_sub = %s{account_filter}
        )
        SELECT ticket, account_name, symbol, side, volume, entry_price,
               current_price, stop_loss, take_profit, floating_pnl, captured_at
        FROM forex_position_snapshots
        WHERE owner_sub = %s{account_filter}
          AND captured_at = (SELECT captured_at FROM latest)
        ORDER BY symbol, ticket
        LIMIT %s
    """
    values = [owner_sub, *account_values, owner_sub, *account_values, limit]
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, values)
        rows = cursor.fetchall()
    return [
        PositionSnapshot(
            ticket=str(row[0]),
            account_name=str(row[1]),
            symbol=str(row[2]),
            side=str(row[3]),
            volume=float(row[4]),
            entry_price=float(row[5]),
            current_price=float(row[6]),
            stop_loss=float(row[7]) if row[7] is not None else None,
            take_profit=float(row[8]) if row[8] is not None else None,
            floating_pnl=float(row[9]),
            captured_at=row[10],
        )
        for row in rows
    ]


def ingest_sync_payload(
    database_url: str,
    owner_sub: str,
    payload: ForexSyncPayload,
) -> SyncIngestResult:
    _validate(database_url, owner_sub, 1)
    with psycopg.connect(database_url, connect_timeout=8) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM forex_sync_batches
                WHERE owner_sub = %s AND payload_hash = %s
                """,
                (owner_sub, payload.payload_hash),
            )
            if cursor.fetchone() is not None:
                return SyncIngestResult(
                    duplicate_batch=True,
                    inserted_positions=0,
                    inserted_deals=0,
                )

            account = payload.account
            cursor.execute(
                """
                INSERT INTO forex_account_snapshots (
                    owner_sub, account_name, balance, equity, floating_pnl,
                    margin_level_percent, captured_at, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (owner_sub, account_name, captured_at) DO NOTHING
                """,
                (
                    owner_sub,
                    account.account_name,
                    account.balance,
                    account.equity,
                    account.floating_pnl,
                    account.margin_level_percent,
                    account.captured_at,
                    payload.source,
                ),
            )

            inserted_positions = 0
            for position in payload.positions:
                cursor.execute(
                    """
                    INSERT INTO forex_position_snapshots (
                        owner_sub, account_name, ticket, symbol, side, volume,
                        entry_price, current_price, stop_loss, take_profit,
                        floating_pnl, captured_at, source
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (
                        owner_sub, account_name, ticket, captured_at
                    ) DO NOTHING
                    """,
                    (
                        owner_sub,
                        position.account_name,
                        position.ticket,
                        position.symbol,
                        position.side,
                        position.volume,
                        position.entry_price,
                        position.current_price,
                        position.stop_loss,
                        position.take_profit,
                        position.floating_pnl,
                        position.captured_at,
                        payload.source,
                    ),
                )
                inserted_positions += cursor.rowcount

            inserted_deals = 0
            for deal in payload.deals:
                cursor.execute(
                    """
                    INSERT INTO forex_deals (
                        owner_sub, ticket, account_name, symbol, side, volume,
                        entry_price, exit_price, opened_at, closed_at,
                        realized_pnl, commission, swap, fee, result_r, source
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (owner_sub, account_name, ticket) DO NOTHING
                    """,
                    (
                        owner_sub,
                        deal.ticket,
                        deal.account_name,
                        deal.symbol,
                        deal.side,
                        deal.volume,
                        deal.entry_price,
                        deal.exit_price,
                        deal.opened_at,
                        deal.closed_at,
                        deal.realized_pnl,
                        deal.commission,
                        deal.swap,
                        deal.fee,
                        deal.result_r,
                        payload.source,
                    ),
                )
                inserted_deals += cursor.rowcount

            cursor.execute(
                """
                INSERT INTO forex_sync_batches (
                    owner_sub, account_name, source, captured_at,
                    snapshot_count, position_count, deal_count,
                    inserted_position_count, inserted_deal_count, payload_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    owner_sub,
                    account.account_name,
                    payload.source,
                    payload.captured_at,
                    1,
                    len(payload.positions),
                    len(payload.deals),
                    inserted_positions,
                    inserted_deals,
                    payload.payload_hash,
                ),
            )
        connection.commit()

    return SyncIngestResult(
        duplicate_batch=False,
        inserted_positions=inserted_positions,
        inserted_deals=inserted_deals,
    )
