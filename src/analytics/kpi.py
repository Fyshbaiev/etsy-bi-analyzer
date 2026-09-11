"""Business KPI calculations.

All formulas are defined in docs/metrics.md. Every metric has exactly
one implementation here. The rest of the application (UI, Excel,
insights) reads only from this module.

Revenue metrics come from the `payments` table, never from `orders`.
`orders` is used only for geography and cross-checks.

Joins use LEFT JOIN because FK constraints are intentionally absent
(see docs/adr/003-no-foreign-keys.md).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KPI:
    """Aggregated key performance indicators for the whole shop."""

    gross_revenue: float = 0.0
    fees: float = 0.0
    net_revenue: float = 0.0
    refunds: float = 0.0
    net_after_refunds: float = 0.0
    orders_count: int = 0
    items_sold: int = 0
    average_order_value: float = 0.0
    average_item_value: float = 0.0
    fee_ratio: float = 0.0
    refund_rate: float = 0.0
    items_per_order: float = 0.0


def _safe_div(a: float, b: float) -> float:
    """Return a / b, or 0.0 when b is zero."""
    return a / b if b else 0.0


def compute_kpi(conn: sqlite3.Connection) -> KPI:
    """Compute the full KPI set from payments and order_items."""
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(gross_amount), 0)  AS gross,
            COALESCE(SUM(fees), 0)          AS fees,
            COALESCE(SUM(net_amount), 0)    AS net,
            COALESCE(SUM(refund_amount), 0) AS refunds,
            COUNT(DISTINCT order_id)        AS orders
        FROM payments
        """
    ).fetchone()

    gross = float(row["gross"])
    fees = float(row["fees"])
    net = float(row["net"])
    refunds = float(row["refunds"])
    orders = int(row["orders"])

    items_row = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS units FROM order_items"
    ).fetchone()
    items_sold = int(items_row["units"])

    kpi = KPI(
        gross_revenue=gross,
        fees=fees,
        net_revenue=net,
        refunds=refunds,
        net_after_refunds=net - refunds,
        orders_count=orders,
        items_sold=items_sold,
        average_order_value=_safe_div(gross, orders),
        average_item_value=_safe_div(gross, items_sold),
        fee_ratio=_safe_div(fees, gross),
        refund_rate=_safe_div(refunds, gross),
        items_per_order=_safe_div(items_sold, orders),
    )
    return kpi


def revenue_by_country(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return revenue aggregated by ship country, descending.

    Uses LEFT JOIN: an order row may be missing for a given payment
    (see ADR-003). Payments without a matching order are grouped
    under 'UNKNOWN'.
    """
    rows = conn.execute(
        """
        SELECT
            COALESCE(o.ship_country, 'UNKNOWN') AS country,
            SUM(p.gross_amount) AS revenue,
            COUNT(DISTINCT p.order_id) AS orders
        FROM payments p
        LEFT JOIN orders o ON o.order_id = p.order_id
        GROUP BY country
        ORDER BY revenue DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def revenue_by_period(
    conn: sqlite3.Connection, period: str = "month"
) -> list[dict[str, Any]]:
    """Return revenue grouped by day, week, or month.

    period is one of: 'day', 'week', 'month'.
    """
    fmt = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%W",
        "month": "%Y-%m",
    }.get(period)
    if fmt is None:
        raise ValueError(f"Unknown period: {period!r}")

    rows = conn.execute(
        """
        SELECT
            strftime(?, order_date) AS period,
            SUM(gross_amount) AS revenue,
            COUNT(DISTINCT order_id) AS orders
        FROM payments
        WHERE order_date IS NOT NULL
        GROUP BY period
        ORDER BY period
        """,
        (fmt,),
    ).fetchall()
    return [dict(r) for r in rows]


def top_listings_by_revenue(
    conn: sqlite3.Connection, limit: int = 10
) -> list[dict[str, Any]]:
    """Return top listings by total item revenue."""
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