"""Tests for src/importer/parsers/order_items.py."""

from pathlib import Path

import pytest

from src.importer.parsers.order_items import (
    MissingColumnsError,
    OrderItemsParseError,
    parse_order_items,
)


HEADER = (
    '"Sale Date","Item Name","Quantity","Price","Item Total","Currency",'
    '"Transaction ID","Listing ID","Order ID","SKU"\n'
)
ROW1 = '01/01/26,"Widget A",2,3.50,7.00,USD,TX1,LST1,ORD1,SKU1\n'
ROW2 = '01/02/26,"Widget B",1,5.00,5.00,USD,TX2,LST2,ORD2,\n'


def test_parses_valid_file(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text(HEADER + ROW1 + ROW2, encoding="utf-8")
    rows = parse_order_items(p)
    assert len(rows) == 2
    assert rows[0]["transaction_id"] == "TX1"
    assert rows[0]["listing_id"] == "LST1"
    assert rows[0]["quantity"] == 2
    assert rows[0]["item_total"] == 7.0
    assert rows[1]["sku"] is None


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(OrderItemsParseError):
        parse_order_items(tmp_path / "nope.csv")


def test_missing_columns_raises(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text('"Foo"\n1\n', encoding="utf-8")
    with pytest.raises(MissingColumnsError):
        parse_order_items(p)


def test_invalid_quantity_raises(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text(
        HEADER + '01/01/26,"X",abc,1.0,1.0,USD,TX,LST,ORD,\n',
        encoding="utf-8",
    )
    with pytest.raises(OrderItemsParseError):
        parse_order_items(p)