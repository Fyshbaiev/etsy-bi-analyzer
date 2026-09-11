"""Cross-table reconciliation checks.

Each check compares data from two or more tables and records
discrepancies in the `data_quality_issues` table.

Severity levels follow docs/reconciliation.md:
  - INFO    expected event, recorded for the record
  - WARNING discrepancy that needs attention
  - ERROR   data cannot be trusted

Checks use LEFT JOIN or NOT EXISTS to tolerate missing parents,
because FK constraints are intentionally absent (see ADR-003).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable

from src.database.repositories import issues_repo


# Tolerance for float comparisons on monetary amounts.
AMOUNT_TOLERANCE = 0.01


@dataclass
class CheckResult:
    """Outcome of one reconciliation check."""

    name: str
    issues_found: int


def _add(
    conn: sqlite3.Connection,
    check_name: str,
    severity: str,
    message: str,
    *,
    table_name: str | None = None,
    row_ref: str | None = None,
) -> None:
    issues_repo.add_issue(
        conn,
        check_name=check_name,
        severity=severity,
        message=message,
        table_name=table_name,
        row_ref=row_ref,
    )


# ---------------------------------------------------------------
# Check 1: Orders ↔ Payments
# ---------------------------------------------------------------

def check_orders_without_payments(conn: sqlite3.Connection) -> int:
    """Orders that have no matching payment record."""
    rows = conn.execute(
        """
        SELECT o.order_id
        FROM orders o
        WHERE NOT EXISTS (
            SELECT 1 FROM payments p WHERE p.order_id = o.order_id
        )
        """
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "order_without_payment",
            "WARNING",
            f"Order {r['order_id']} has no payment record.",
            table_name="orders",
            row_ref=r["order_id"],
        )
    return len(rows)


def check_payments_without_orders(conn: sqlite3.Connection) -> int:
    """Payments that have no matching order."""
    rows = conn.execute(
        """
        SELECT p.payment_id, p.order_id
        FROM payments p
        WHERE NOT EXISTS (
            SELECT 1 FROM orders o WHERE o.order_id = p.order_id
        )
        """
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "payment_without_order",
            "ERROR",
            f"Payment {r['payment_id']} references missing order "
            f"{r['order_id']}.",
            table_name="payments",
            row_ref=r["payment_id"],
        )
    return len(rows)


def check_payment_amounts(conn: sqlite3.Connection) -> int:
    """Payments whose gross amount does not match order value minus discount."""
    rows = conn.execute(
        """
        SELECT
            p.payment_id,
            p.order_id,
            p.gross_amount,
            o.order_value,
            o.discount_amount,
            (o.order_value - o.discount_amount) AS expected
        FROM payments p
        JOIN orders o ON o.order_id = p.order_id
        WHERE ABS(p.gross_amount - (o.order_value - o.discount_amount)) > ?
        """,
        (AMOUNT_TOLERANCE,),
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "payment_amount_mismatch",
            "WARNING",
            f"Payment {r['payment_id']} gross {r['gross_amount']} != "
            f"expected {r['expected']}.",
            table_name="payments",
            row_ref=r["payment_id"],
        )
    return len(rows)


def check_payment_fees(conn: sqlite3.Connection) -> int:
    """Payments whose fees do not match order card processing fees."""
    rows = conn.execute(
        """
        SELECT p.payment_id, p.fees, o.card_processing_fees
        FROM payments p
        JOIN orders o ON o.order_id = p.order_id
        WHERE ABS(p.fees - o.card_processing_fees) > ?
        """,
        (AMOUNT_TOLERANCE,),
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "payment_fees_mismatch",
            "WARNING",
            f"Payment {r['payment_id']} fees {r['fees']} != "
            f"order card fees {r['card_processing_fees']}.",
            table_name="payments",
            row_ref=r["payment_id"],
        )
    return len(rows)


def check_payment_net(conn: sqlite3.Connection) -> int:
    """Payments whose net amount does not match order net."""
    rows = conn.execute(
        """
        SELECT p.payment_id, p.net_amount, o.order_net
        FROM payments p
        JOIN orders o ON o.order_id = p.order_id
        WHERE ABS(p.net_amount - o.order_net) > ?
        """,
        (AMOUNT_TOLERANCE,),
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "payment_net_mismatch",
            "WARNING",
            f"Payment {r['payment_id']} net {r['net_amount']} != "
            f"order net {r['order_net']}.",
            table_name="payments",
            row_ref=r["payment_id"],
        )
    return len(rows)


# ---------------------------------------------------------------
# Check 2: Orders ↔ Order Items
# ---------------------------------------------------------------

def check_orders_without_items(conn: sqlite3.Connection) -> int:
    """Orders that have no line items."""
    rows = conn.execute(
        """
        SELECT o.order_id
        FROM orders o
        WHERE NOT EXISTS (
            SELECT 1 FROM order_items i WHERE i.order_id = o.order_id
        )
        """
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "order_without_items",
            "INFO",
            f"Order {r['order_id']} has no line items.",
            table_name="orders",
            row_ref=r["order_id"],
        )
    return len(rows)


def check_items_without_orders(conn: sqlite3.Connection) -> int:
    """Line items whose order_id is not present in orders."""
    rows = conn.execute(
        """
        SELECT i.transaction_id, i.order_id
        FROM order_items i
        WHERE NOT EXISTS (
            SELECT 1 FROM orders o WHERE o.order_id = i.order_id
        )
        """
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "item_without_order",
            "ERROR",
            f"Item {r['transaction_id']} references missing order "
            f"{r['order_id']}.",
            table_name="order_items",
            row_ref=r["transaction_id"],
        )
    return len(rows)


def check_item_totals(conn: sqlite3.Connection) -> int:
    """Items whose item_total != price * quantity."""
    rows = conn.execute(
        """
        SELECT transaction_id, price, quantity, item_total
        FROM order_items
        WHERE ABS(item_total - (price * quantity)) > ?
        """,
        (AMOUNT_TOLERANCE,),
    ).fetchall()
    for r in rows:
        expected = r["price"] * r["quantity"]
        _add(
            conn,
            "item_total_mismatch",
            "WARNING",
            f"Item {r['transaction_id']} total {r['item_total']} != "
            f"expected {expected}.",
            table_name="order_items",
            row_ref=r["transaction_id"],
        )
    return len(rows)


# ---------------------------------------------------------------
# Check 3: Refunds
# ---------------------------------------------------------------

def record_refunds(conn: sqlite3.Connection) -> int:
    """Record every payment with a non-zero refund as INFO."""
    rows = conn.execute(
        """
        SELECT payment_id, order_id, refund_amount
        FROM payments
        WHERE refund_amount > 0
        """
    ).fetchall()
    for r in rows:
        _add(
            conn,
            "refund_recorded",
            "INFO",
            f"Refund of {r['refund_amount']} on order {r['order_id']}.",
            table_name="payments",
            row_ref=r["payment_id"],
        )
    return len(rows)


# ---------------------------------------------------------------
# Check 4: Currency consistency
# ---------------------------------------------------------------

def check_currency(conn: sqlite3.Connection) -> int:
    """Rows in payments or orders with a non-USD currency."""
    total = 0
    for table in ("orders", "payments", "order_items"):
        rows = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE currency != 'USD'"
        ).fetchone()
        count = int(rows[0])
        if count > 0:
            _add(
                conn,
                "non_usd_currency",
                "ERROR",
                f"{count} rows in {table} use a non-USD currency.",
                table_name=table,
            )
            total += count
    return total


# ---------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------

_CHECKS: list[tuple[str, Callable[[sqlite3.Connection], int]]] = [
    ("orders_without_payments", check_orders_without_payments),
    ("payments_without_orders", check_payments_without_orders),
    ("payment_amounts", check_payment_amounts),
    ("payment_fees", check_payment_fees),
    ("payment_net", check_payment_net),
    ("orders_without_items", check_orders_without_items),
    ("items_without_orders", check_items_without_orders),
    ("item_totals", check_item_totals),
    ("refunds", record_refunds),
    ("currency", check_currency),
]


def run_all_checks(conn: sqlite3.Connection) -> list[CheckResult]:
    """Run every reconciliation check and return per-check results."""
    results: list[CheckResult] = []
    for name, fn in _CHECKS:
        issues = fn(conn)
        results.append(CheckResult(name=name, issues_found=issues))
    return results