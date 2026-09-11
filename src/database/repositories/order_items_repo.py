"""Repository for the `order_items` table."""

from __future__ import annotations

import sqlite3
from typing import Any


_INSERT_SQL = """
INSERT OR IGNORE INTO order_items (
    transaction_id, order_id, sale_date, listing_id, item_name,
    quantity, price, item_total, currency, sku, import_id
) VALUES (
    :transaction_id, :order_id, :sale_date, :listing_id, :item_name,
    :quantity, :price, :item_total, :currency, :sku, :import_id
)
"""


def insert_order_items(
    conn: sqlite3.Connection,
    items: list[dict[str, Any]],
    import_id: int,
) -> int:
    if not items:
        return 0
    enriched = [{**i, "import_id": import_id} for i in items]
    before = conn.total_changes
    conn.executemany(_INSERT_SQL, enriched)
    conn.commit()
    return conn.total_changes - before


def count_order_items(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0])


def sum_item_total(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT COALESCE(SUM(item_total), 0) FROM order_items").fetchone()
    return float(row[0])


def top_listings_by_revenue(
    conn: sqlite3.Connection, limit: int = 10
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            listing_id,
            MAX(item_name) AS item_name,
            SUM(item_total) AS revenue,
            SUM(quantity) AS units,
            COUNT(DISTINCT order_id) AS orders
        FROM order_items
        GROUP BY listing_id
        ORDER BY revenue DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]