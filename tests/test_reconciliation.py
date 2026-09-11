"""Tests for src/analytics/reconciliation.py."""

from pathlib import Path

import pytest

from src.analytics import reconciliation as rec
from src.database.connection import connect_and_init
from src.database.repositories import (
    imports_repo,
    issues_repo,
    order_items_repo,
    orders_repo,
    payments_repo,
)


@pytest.fixture()
def conn(tmp_path: Path):
    connection = connect_and_init(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture()
def import_id(conn) -> int:
    return imports_repo.create_import(conn, "x.csv", "mixed", "h-mix")


def _order(order_id: str, **overrides) -> dict:
    base = {
        "order_id": order_id,
        "sale_date": "2026-01-15",
        "currency": "USD",
        "order_value": 10.0,
        "discount_amount": 0.0,
        "order_total": 10.0,
        "card_processing_fees": 1.0,
        "order_net": 9.0,
    }
    base.update(overrides)
    return base


def _payment(order_id: str, **overrides) -> dict:
    base = {
        "payment_id": f"p-{order_id}",
        "order_id": order_id,
        "gross_amount": 10.0,
        "fees": 1.0,
        "net_amount": 9.0,
        "refund_amount": 0.0,
        "currency": "USD",
        "order_date": "2026-01-15",
        "funds_available": "2026-01-18",
        "status": "SETTLED",
    }
    base.update(overrides)
    return base


def _item(order_id: str, txn: str, **overrides) -> dict:
    base = {
        "transaction_id": txn,
        "order_id": order_id,
        "sale_date": "2026-01-15",
        "listing_id": "L1",
        "item_name": "X",
        "quantity": 1,
        "price": 10.0,
        "item_total": 10.0,
        "currency": "USD",
        "sku": None,
    }
    base.update(overrides)
    return base


# --- check 1: orders <-> payments ---

def test_order_without_payment_is_warned(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    count = rec.check_orders_without_payments(conn)
    assert count == 1
    issues = issues_repo.list_issues(conn, severity="WARNING")
    assert any(i["check_name"] == "order_without_payment" for i in issues)


def test_payment_without_order_is_error(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("9999")], import_id)
    count = rec.check_payments_without_orders(conn)
    assert count == 1
    issues = issues_repo.list_issues(conn, severity="ERROR")
    assert any(i["check_name"] == "payment_without_order" for i in issues)


def test_matching_payments_produce_no_issues(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    assert rec.check_orders_without_payments(conn) == 0
    assert rec.check_payments_without_orders(conn) == 0


def test_payment_amount_mismatch(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    payments_repo.insert_payments(
        conn, [_payment("1001", gross_amount=99.99)], import_id
    )
    count = rec.check_payment_amounts(conn)
    assert count == 1
    issues = issues_repo.list_issues(conn, severity="WARNING")
    assert any(i["check_name"] == "payment_amount_mismatch" for i in issues)


def test_payment_fees_mismatch(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    payments_repo.insert_payments(
        conn, [_payment("1001", fees=5.0)], import_id
    )
    assert rec.check_payment_fees(conn) == 1


def test_payment_net_mismatch(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    payments_repo.insert_payments(
        conn, [_payment("1001", net_amount=1.0)], import_id
    )
    assert rec.check_payment_net(conn) == 1


# --- check 2: orders <-> items ---

def test_order_without_items_is_info(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    assert rec.check_orders_without_items(conn) == 1
    issues = issues_repo.list_issues(conn, severity="INFO")
    assert any(i["check_name"] == "order_without_items" for i in issues)


def test_item_without_order_is_error(conn, import_id) -> None:
    order_items_repo.insert_order_items(
        conn, [_item("9999", "tx1")], import_id
    )
    assert rec.check_items_without_orders(conn) == 1


def test_item_total_mismatch(conn, import_id) -> None:
    order_items_repo.insert_order_items(
        conn,
        [_item("1001", "tx1", price=3.0, quantity=2, item_total=99.0)],
        import_id,
    )
    assert rec.check_item_totals(conn) == 1


def test_correct_items_produce_no_issues(conn, import_id) -> None:
    order_items_repo.insert_order_items(
        conn,
        [_item("1001", "tx1", price=3.0, quantity=2, item_total=6.0)],
        import_id,
    )
    assert rec.check_item_totals(conn) == 0


# --- check 3: refunds ---

def test_refunds_are_recorded(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn,
        [
            _payment("1001", refund_amount=2.5),
            _payment("1002", refund_amount=0.0),
        ],
        import_id,
    )
    count = rec.record_refunds(conn)
    assert count == 1
    issues = issues_repo.list_issues(conn, severity="INFO")
    assert any(i["check_name"] == "refund_recorded" for i in issues)


# --- check 4: currency ---

def test_non_usd_currency_is_error(conn, import_id) -> None:
    orders_repo.insert_orders(
        conn, [_order("1001", currency="EUR")], import_id
    )
    count = rec.check_currency(conn)
    assert count == 1
    issues = issues_repo.list_issues(conn, severity="ERROR")
    assert any(i["check_name"] == "non_usd_currency" for i in issues)


# --- orchestrator ---

def test_run_all_checks_returns_all_results(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_order("1001")], import_id)
    payments_repo.insert_payments(conn, [_payment("9999")], import_id)

    results = rec.run_all_checks(conn)
    names = {r.name for r in results}
    assert "orders_without_payments" in names
    assert "payments_without_orders" in names
    assert "currency" in names
    assert len(results) >= 10