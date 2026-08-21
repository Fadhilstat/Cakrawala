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


def list_portfolio_transactions(
    database_url: str,
    owner_sub: str,
    *,
    limit: int = 50,
) -> list[PortfolioTransaction]:
    if not database_url:
        raise ValueError("database_url is required")
    if not owner_sub or len(owner_sub) > 255:
        raise ValueError("owner_sub is invalid")
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
