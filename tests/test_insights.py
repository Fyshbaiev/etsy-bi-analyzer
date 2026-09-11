"""Tests for src/insights/rules.py."""

from pathlib import Path

import pytest

from src.database.connection import connect_and_init
from src.database.repositories import (
    imports_repo,
    issues_repo,
    order_items_repo,
    orders_repo,
    payments_repo,
)
from src.insights import rules


@pytest.fixture()
def conn(tmp_path: Path):
    connection = connect_and_init(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture()
def import_id(conn) -> int:
    return imports_repo.create_import(conn, "x.csv", "mixed", "h-mix")


def _payment(order_id: str, **overrides) -> dict:
    base = {
        "payment_id": f"p-{order_id}",
        "order_id": order_id,
        "gross_amount": 100.0,
        "fees": 10.0,
        "net_amount": 90.0,
        "refund_amount": 0.0,
        "currency": "USD",
        "order_date": "2026-01-15",
        "funds_available": "2026-01-18",
        "status": "SETTLED",
    }
    base.update(overrides)
    return base


def _item(order_id: str, txn: str, listing: str, **overrides) -> dict:
    base = {
        "transaction_id": txn,
        "order_id": order_id,
        "sale_date": "2026-01-15",
        "listing_id": listing,
        "item_name": f"Item {listing}",
        "quantity": 1,
        "price": 100.0,
        "item_total": 100.0,
        "currency": "USD",
        "sku": None,
    }
    base.update(overrides)
    return base


def _codes(findings) -> set[str]:
    return {f.code for f in findings}


# ---------------------------------------------------------------

def test_no_data_returns_only_no_data_rule(conn) -> None:
    findings = rules.generate_insights(conn)
    assert len(findings) == 1
    assert findings[0].code == "no_data"
    assert findings[0].severity == rules.Severity.WARNING


def test_normal_fee_ratio_is_info(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn, [_payment("1001", fees=8.0, net_amount=92.0)], import_id
    )
    findings = rules.generate_insights(conn)
    assert "normal_fee_ratio" in _codes(findings)


def test_high_fee_ratio_is_warning(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn, [_payment("1001", fees=20.0, net_amount=80.0)], import_id
    )
    findings = rules.generate_insights(conn)
    high = [f for f in findings if f.code == "high_fee_ratio"]
    assert len(high) == 1
    assert high[0].severity == rules.Severity.WARNING


def test_no_refunds_info(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    findings = rules.generate_insights(conn)
    assert "no_refunds" in _codes(findings)


def test_high_refund_rate_is_risk(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn,
        [_payment("1001", refund_amount=10.0)],
        import_id,
    )
    findings = rules.generate_insights(conn)
    high = [f for f in findings if f.code == "high_refund_rate"]
    assert len(high) == 1
    assert high[0].severity == rules.Severity.RISK


def test_average_order_value_rule(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn,
        [
            _payment("1001", gross_amount=50.0),
            _payment("1002", gross_amount=150.0),
        ],
        import_id,
    )
    findings = rules.generate_insights(conn)
    aov = [f for f in findings if f.code == "average_order_value"]
    assert len(aov) == 1
    assert "$100.00" in aov[0].title


def test_best_performer_rule(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    order_items_repo.insert_order_items(
        conn,
        [
            _item("1001", "tx1", "L1", item_total=500.0),
            _item("1002", "tx2", "L2", item_total=100.0),
        ],
        import_id,
    )
    findings = rules.generate_insights(conn)
    best = [f for f in findings if f.code == "best_performer"]
    assert len(best) == 1
    assert "Item L1" in best[0].title


def test_revenue_concentration_warning(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    # One listing dominates.
    order_items_repo.insert_order_items(
        conn,
        [
            _item("1001", "tx1", "L1", item_total=900.0),
            _item("1002", "tx2", "L2", item_total=50.0),
            _item("1003", "tx3", "L3", item_total=50.0),
        ],
        import_id,
    )
    findings = rules.generate_insights(conn)
    conc = [f for f in findings if f.code == "revenue_concentration"]
    assert len(conc) == 1
    assert conc[0].severity == rules.Severity.WARNING


def test_data_quality_clean_when_no_issues(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    findings = rules.generate_insights(conn)
    assert "data_quality_clean" in _codes(findings)


def test_data_quality_errors_are_risk(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    issues_repo.add_issue(
        conn, "test_error", "ERROR", "boom", table_name="orders"
    )
    findings = rules.generate_insights(conn)
    errors = [f for f in findings if f.code == "data_quality_errors"]
    assert len(errors) == 1
    assert errors[0].severity == rules.Severity.RISK


def test_insights_have_title_and_detail(conn, import_id) -> None:
    payments_repo.insert_payments(conn, [_payment("1001")], import_id)
    order_items_repo.insert_order_items(
        conn, [_item("1001", "tx1", "L1")], import_id
    )
    findings = rules.generate_insights(conn)
    for f in findings:
        assert f.title
        assert f.detail