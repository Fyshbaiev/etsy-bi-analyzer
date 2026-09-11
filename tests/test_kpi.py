"""Tests for src/analytics/kpi.py."""

from pathlib import Path

import pytest

from src.analytics import kpi as kpi_module
from src.database.connection import connect_and_init
from src.database.repositories import (
    imports_repo,
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
    return imports_repo.create_import(conn, "x.csv", "mixed", "hash-mixed")


def _payment(order_id: str, **overrides) -> dict:
    base = {
        "payment_id": f"pay-{order_id}",
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


def _item(order_id: str, txn: str, listing: str, **overrides) -> dict:
    base = {
        "transaction_id": txn,
        "order_id": order_id,
        "sale_date": "2026-01-15",
        "listing_id": listing,
        "item_name": f"Item {listing}",
        "quantity": 1,
        "price": 10.0,
        "item_total": 10.0,
        "currency": "USD",
        "sku": None,
    }
    base.update(overrides)
    return base


def test_empty_database_returns_zero_kpi(conn) -> None:
    result = kpi_module.compute_kpi(conn)
    assert result.gross_revenue == 0.0
    assert result.orders_count == 0
    assert result.average_order_value == 0.0
    assert result.fee_ratio == 0.0
    assert result.refund_rate == 0.0


def test_basic_kpi(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn,
        [
            _payment("1001", gross_amount=20.0, fees=2.0, net_amount=18.0),
            _payment("1002", gross_amount=30.0, fees=3.0, net_amount=27.0),
        ],
        import_id,
    )
    order_items_repo.insert_order_items(
        conn,
        [
            _item("1001", "tx1", "L1", quantity=2, item_total=20.0),
            _item("1002", "tx2", "L2", quantity=1, item_total=30.0),
        ],
        import_id,
    )

    result = kpi_module.compute_kpi(conn)
    assert result.gross_revenue == 50.0
    assert result.fees == 5.0
    assert result.net_revenue == 45.0
    assert result.refunds == 0.0
    assert result.net_after_refunds == 45.0
    assert result.orders_count == 2
    assert result.items_sold == 3
    assert result.average_order_value == pytest.approx(25.0)
    assert result.average_item_value == pytest.approx(50.0 / 3)
    assert result.fee_ratio == pytest.approx(0.1)
    assert result.refund_rate == 0.0
    assert result.items_per_order == pytest.approx(1.5)


def test_refunds_reduce_net_after_refunds(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn,
        [
            _payment("1001", gross_amount=100.0, fees=10.0, net_amount=90.0,
                     refund_amount=25.0),
        ],
        import_id,
    )
    result = kpi_module.compute_kpi(conn)
    assert result.gross_revenue == 100.0
    assert result.refunds == 25.0
    assert result.net_revenue == 90.0
    assert result.net_after_refunds == 65.0
    assert result.refund_rate == pytest.approx(0.25)


def test_revenue_by_country_uses_left_join(conn, import_id) -> None:
    orders_repo.insert_orders(
        conn,
        [{
            "order_id": "1001", "sale_date": "2026-01-15", "currency": "USD",
            "order_value": 20.0, "discount_amount": 0.0, "order_total": 20.0,
            "card_processing_fees": 2.0, "order_net": 18.0,
        }],
        import_id,
    )
    # Give the order a country.
    conn.execute(
        "UPDATE orders SET ship_country = 'Germany' WHERE order_id = '1001'"
    )
    conn.commit()

    payments_repo.insert_payments(
        conn,
        [
            _payment("1001", gross_amount=20.0),
            _payment("9999", gross_amount=5.0),  # orphan, no order row
        ],
        import_id,
    )

    rows = kpi_module.revenue_by_country(conn)
    by_country = {r["country"]: r for r in rows}
    assert "Germany" in by_country
    assert by_country["Germany"]["revenue"] == 20.0
    # Orphan payment appears under UNKNOWN because of LEFT JOIN.
    assert "UNKNOWN" in by_country
    assert by_country["UNKNOWN"]["revenue"] == 5.0


def test_revenue_by_period_month(conn, import_id) -> None:
    payments_repo.insert_payments(
        conn,
        [
            _payment("1001", order_date="2026-01-05", gross_amount=10.0),
            _payment("1002", order_date="2026-01-20", gross_amount=15.0),
            _payment("1003", order_date="2026-02-01", gross_amount=30.0),
        ],
        import_id,
    )
    rows = kpi_module.revenue_by_period(conn, period="month")
    by_period = {r["period"]: r for r in rows}
    assert by_period["2026-01"]["revenue"] == 25.0
    assert by_period["2026-02"]["revenue"] == 30.0


def test_revenue_by_period_invalid_period(conn) -> None:
    with pytest.raises(ValueError):
        kpi_module.revenue_by_period(conn, period="year")


def test_top_listings_by_revenue(conn, import_id) -> None:
    order_items_repo.insert_order_items(
        conn,
        [
            _item("1001", "tx1", "L1", item_total=50.0),
            _item("1001", "tx2", "L2", item_total=10.0),
            _item("1002", "tx3", "L1", item_total=40.0),
        ],
        import_id,
    )
    rows = kpi_module.top_listings_by_revenue(conn, limit=5)
    assert rows[0]["listing_id"] == "L1"
    assert rows[0]["revenue"] == 90.0
    assert rows[0]["orders"] == 2
    assert rows[1]["listing_id"] == "L2"