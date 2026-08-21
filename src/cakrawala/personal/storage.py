from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import psycopg


@dataclass(frozen=True)
class PortfolioTransaction:
    asset: str
    side: str
    quantity: Decimal
    price: Decimal
    executed_at: datetime


@dataclass(frozen=True)
class TradePlan:
    asset: str
    direction: str
    entry: Decimal | None
    stop: Decimal | None
    target: Decimal | None
    risk_percent: Decimal
    thesis: str
    invalidation: str
    created_at: datetime


@dataclass(frozen=True)
class JournalEntry:
    asset: str
    direction: str
    result_r: Decimal
    notes: str
    lesson: str
    executed_at: datetime


@dataclass(frozen=True)
class PlaybookEntry:
    name: str
    setup: str
    entry_rules: str
    risk_rules: str
    exit_rules: str
    created_at: datetime


def _validate_access(database_url: str, owner_sub: str) -> None:
    if not database_url:
        raise ValueError("database_url is required")
    if not owner_sub or len(owner_sub) > 255:
        raise ValueError("owner_sub is invalid")


def list_portfolio_transactions(
    database_url: str,
    owner_sub: str,
    *,
    limit: int = 50,
) -> list[PortfolioTransaction]:
    _validate_access(database_url, owner_sub)
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    query = """
        SELECT asset, side, quantity, price, executed_at
        FROM portfolio_transactions
        WHERE owner_sub = %s
        ORDER BY executed_at DESC
        LIMIT %s
    """
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, (owner_sub, limit))
        rows = cursor.fetchall()

    return [
        PortfolioTransaction(
            asset=str(row[0]),
            side=str(row[1]),
            quantity=row[2],
            price=row[3],
            executed_at=row[4],
        )
        for row in rows
    ]


def add_trade_plan(
    database_url: str,
    owner_sub: str,
    *,
    asset: str,
    direction: str,
    entry: float | None,
    stop: float | None,
    target: float | None,
    risk_percent: float,
    thesis: str,
    invalidation: str,
) -> None:
    _validate_access(database_url, owner_sub)
    if direction not in {"LONG", "SHORT", "WAIT"}:
        raise ValueError("direction is invalid")
    if not 0 < risk_percent <= 10:
        raise ValueError("risk_percent must be between 0 and 10")
    if not asset.strip() or not thesis.strip() or not invalidation.strip():
        raise ValueError("asset, thesis, and invalidation are required")

    query = """
        INSERT INTO trade_plans (
            owner_sub, asset, direction, entry, stop, target,
            risk_percent, thesis, invalidation
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        owner_sub,
        asset.strip().upper(),
        direction,
        entry,
        stop,
        target,
        risk_percent,
        thesis.strip(),
        invalidation.strip(),
    )
    with psycopg.connect(database_url, connect_timeout=8) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
        connection.commit()


def list_trade_plans(
    database_url: str,
    owner_sub: str,
    *,
    limit: int = 30,
) -> list[TradePlan]:
    _validate_access(database_url, owner_sub)
    query = """
        SELECT asset, direction, entry, stop, target, risk_percent,
               thesis, invalidation, created_at
        FROM trade_plans
        WHERE owner_sub = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, (owner_sub, limit))
        rows = cursor.fetchall()
    return [TradePlan(*row) for row in rows]


def add_journal_entry(
    database_url: str,
    owner_sub: str,
    *,
    asset: str,
    direction: str,
    result_r: float,
    notes: str,
    lesson: str,
    executed_at: datetime,
) -> None:
    _validate_access(database_url, owner_sub)
    if direction not in {"LONG", "SHORT"}:
        raise ValueError("direction is invalid")
    if not asset.strip() or not notes.strip() or not lesson.strip():
        raise ValueError("asset, notes, and lesson are required")
    query = """
        INSERT INTO trading_journal (
            owner_sub, asset, direction, result_r, notes, lesson, executed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        owner_sub,
        asset.strip().upper(),
        direction,
        result_r,
        notes.strip(),
        lesson.strip(),
        executed_at,
    )
    with psycopg.connect(database_url, connect_timeout=8) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
        connection.commit()


def list_journal_entries(
    database_url: str,
    owner_sub: str,
    *,
    limit: int = 50,
) -> list[JournalEntry]:
    _validate_access(database_url, owner_sub)
    query = """
        SELECT asset, direction, result_r, notes, lesson, executed_at
        FROM trading_journal
        WHERE owner_sub = %s
        ORDER BY executed_at DESC
        LIMIT %s
    """
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, (owner_sub, limit))
        rows = cursor.fetchall()
    return [JournalEntry(*row) for row in rows]


def add_playbook_entry(
    database_url: str,
    owner_sub: str,
    *,
    name: str,
    setup: str,
    entry_rules: str,
    risk_rules: str,
    exit_rules: str,
) -> None:
    _validate_access(database_url, owner_sub)
    values = (name, setup, entry_rules, risk_rules, exit_rules)
    if any(not value.strip() for value in values):
        raise ValueError("all playbook fields are required")
    query = """
        INSERT INTO playbook_entries (
            owner_sub, name, setup, entry_rules, risk_rules, exit_rules
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    with psycopg.connect(database_url, connect_timeout=8) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (owner_sub, *(value.strip() for value in values)),
            )
        connection.commit()


def list_playbook_entries(
    database_url: str,
    owner_sub: str,
    *,
    limit: int = 30,
) -> list[PlaybookEntry]:
    _validate_access(database_url, owner_sub)
    query = """
        SELECT name, setup, entry_rules, risk_rules, exit_rules, created_at
        FROM playbook_entries
        WHERE owner_sub = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    with (
        psycopg.connect(database_url, connect_timeout=8) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(query, (owner_sub, limit))
        rows = cursor.fetchall()
    return [PlaybookEntry(*row) for row in rows]
