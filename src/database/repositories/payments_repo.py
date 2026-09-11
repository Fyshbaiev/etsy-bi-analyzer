"""Repository for the `payments` table."""

from __future__ import annotations

import sqlite3
from typing import Any


_INSERT_SQL = """
INSERT OR IGNORE INTO payments (
    payment_id, order_id, gross_amount, fees, net_amount,
    refund_amount, currency, order_date, funds_available,
    status, import_id
) VALUES (
    :payment_id, :order_id, :gross_amount, :fees, :net_amount,
    :refund_amount, :currency, :order_date, :funds_available,
    :status, :import_id
)
"""


def insert_payments(
    conn: sqlite3.Connection,
    payments: list[dict[str, Any]],
    import_id: int,
) -> int:
    if not payments:
        return 0
    enriched = [{**p, "import_id": import_id} for p in payments]
    before = conn.total_changes
    conn.executemany(_INSERT_SQL, enriched)
    conn.commit()
    return conn.total_changes - before


def count_payments(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0])


def sum_net_amount(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT COALESCE(SUM(net_amount), 0) FROM payments").fetchone()
    return float(row[0])


def list_payments(
    conn: sqlite3.Connection, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM payments ORDER BY order_date DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]