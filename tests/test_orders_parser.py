"""Tests for src/importer/parsers/orders.py."""

import csv
from pathlib import Path

import pytest

from src.importer.parsers.orders import (
    MissingColumnsError,
    OrdersParseError,
    parse_orders,
)


SAMPLE = Path(__file__).parent / "fixtures" / "EtsySoldOrders_sample.csv"


def _count_data_rows(path: Path) -> int:
    """Count data rows in the CSV, excluding the header."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def test_parse_sample_returns_all_rows() -> None:
    """The parser must return exactly one dict per CSV data row."""
    rows = parse_orders(SAMPLE)
    expected = _count_data_rows(SAMPLE)
    assert expected > 0
    assert len(rows) == expected


def test_every_row_has_required_keys() -> None:
    """Every row must contain all required normalized keys."""
    required_keys = {
        "order_id",
        "sale_date",
        "currency",
        "order_value",
        "discount_amount",
        "order_total",
        "card_processing_fees",
        "order_net",
    }
    for row in parse_orders(SAMPLE):
        assert required_keys.issubset(row.keys())


def test_types_are_normalized() -> None:
    """Numeric fields must be floats, order_id and currency must be strings."""
    for row in parse_orders(SAMPLE):
        assert isinstance(row["order_id"], str)
        assert row["order_id"] != ""
        assert isinstance(row["currency"], str)
        assert row["currency"] == "USD"
        assert isinstance(row["order_value"], float)
        assert isinstance(row["discount_amount"], float)
        assert isinstance(row["order_total"], float)
        assert isinstance(row["card_processing_fees"], float)
        assert isinstance(row["order_net"], float)


def test_sale_date_is_iso_or_none() -> None:
    """sale_date must be a YYYY-MM-DD string, or None for empty input."""
    for row in parse_orders(SAMPLE):
        value = row["sale_date"]
        if value is not None:
            assert len(value) == 10
            assert value[4] == "-"
            assert value[7] == "-"


def test_order_ids_are_unique_in_sample() -> None:
    """The parser must not merge or duplicate rows."""
    rows = parse_orders(SAMPLE)
    ids = [row["order_id"] for row in rows]
    assert len(ids) == len(set(ids))


def test_first_row_matches_raw_csv() -> None:
    """First normalized row must match the first data row of the CSV."""
    with SAMPLE.open(encoding="utf-8-sig", newline="") as f:
        raw_first = next(csv.DictReader(f))

    parsed_first = parse_orders(SAMPLE)[0]
    assert parsed_first["order_id"] == raw_first["Order ID"].strip()
    assert parsed_first["currency"] == raw_first["Currency"].strip()
    assert parsed_first["order_value"] == float(raw_first["Order Value"])


def test_missing_file_raises() -> None:
    with pytest.raises(OrdersParseError):
        parse_orders(Path("no_such_file.csv"))


def test_missing_columns_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text('"Foo","Bar"\n1,2\n', encoding="utf-8")
    with pytest.raises(MissingColumnsError):
        parse_orders(bad)