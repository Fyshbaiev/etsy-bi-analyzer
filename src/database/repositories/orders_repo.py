"""Repository for the `orders` table.

Uses INSERT OR IGNORE so that re-importing overlapping data does not
raise on duplicate order_id. The number of rows actually inserted is
computed by comparing sqlite3.Connection.total_changes before and after.
"""

from __future__ import annotations

import sqlite3
from typing import Any


_INSERT_SQL = """
INSERT OR IGNORE INTO orders (
    order_id,
    sale_date,
    currency,
    order_value,
    discount_amount,
    order_total,
    card_processing_fees,
    order_net,
    import_id
) VALUES (
    :order_id,
    :sale_date,
    :currency,
    :order_value,
    :discount_amount,
    :order_total,
    :card_processing_fees,
    :order_net,
    :import_id
)
"""


def insert_orders(
    conn: sqlite3.Connection,
    orders: list[dict[str, Any]],
    import_id: int,
) -> int:
    """Insert parsed orders and return the number of rows actually inserted.

    Rows with duplicate order_id are silently skipped.
    """
    if not orders:
        return 0
    enriched = [{**o, "import_id": import_id} for o in orders]
    before = conn.total_changes
    conn.executemany(_INSERT_SQL, enriched)
    conn.commit()
    return conn.total_changes - before


def count_orders(conn: sqlite3.Connection) -> int:
    """Return total number of orders in the database."""
    return int(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0])


def get_order(
    conn: sqlite3.Connection, order_id: str
) -> dict[str, Any] | None:
    """Return a single order by id, or None."""
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    return dict(row) if row else None


def list_orders(
    conn: sqlite3.Connection, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    """Return orders sorted by sale_date descending."""
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY sale_date DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]