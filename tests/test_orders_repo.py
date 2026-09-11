"""Tests for src/database/repositories/orders_repo.py."""

from pathlib import Path

import pytest

from src.database.connection import connect_and_init
from src.database.repositories import imports_repo, orders_repo


@pytest.fixture()
def conn(tmp_path: Path):
    connection = connect_and_init(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture()
def import_id(conn) -> int:
    return imports_repo.create_import(conn, "x.csv", "orders", "h-x")


def _sample_order(order_id: str, **overrides) -> dict:
    base = {
        "order_id": order_id,
        "sale_date": "2026-01-01",
        "currency": "USD",
        "order_value": 6.99,
        "discount_amount": 0.0,
        "order_total": 6.99,
        "card_processing_fees": 0.46,
        "order_net": 6.53,
    }
    base.update(overrides)
    return base


def test_insert_empty_list_returns_zero(conn, import_id) -> None:
    assert orders_repo.insert_orders(conn, [], import_id) == 0


def test_insert_and_count(conn, import_id) -> None:
    inserted = orders_repo.insert_orders(
        conn,
        [_sample_order("1001"), _sample_order("1002")],
        import_id,
    )
    assert inserted == 2
    assert orders_repo.count_orders(conn) == 2


def test_duplicate_order_id_is_skipped(conn, import_id) -> None:
    orders_repo.insert_orders(conn, [_sample_order("1001")], import_id)
    inserted = orders_repo.insert_orders(
        conn, [_sample_order("1001"), _sample_order("1002")], import_id
    )
    assert inserted == 1
    assert orders_repo.count_orders(conn) == 2


def test_get_order_returns_full_record(conn, import_id) -> None:
    orders_repo.insert_orders(
        conn, [_sample_order("1001", order_net=7.5)], import_id
    )
    order = orders_repo.get_order(conn, "1001")
    assert order is not None
    assert order["order_id"] == "1001"
    assert order["order_net"] == 7.5
    assert order["import_id"] == import_id


def test_get_missing_order_returns_none(conn) -> None:
    assert orders_repo.get_order(conn, "missing") is None


def test_list_orders_respects_limit(conn, import_id) -> None:
    for i in range(5):
        orders_repo.insert_orders(
            conn, [_sample_order(f"1{i:03d}")], import_id
        )
    page = orders_repo.list_orders(conn, limit=2)
    assert len(page) == 2