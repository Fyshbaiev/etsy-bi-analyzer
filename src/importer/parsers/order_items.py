"""Parser for EtsySoldOrderItems*.csv files.

One row per line item. The only file with both Order ID and Listing ID,
so all product-level analytics depend on it.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "Sale Date",
    "Order ID",
    "Transaction ID",
    "Listing ID",
    "Quantity",
    "Price",
    "Item Total",
    "Currency",
})


class OrderItemsParseError(Exception):
    """Raised when an order items CSV cannot be parsed."""


class MissingColumnsError(OrderItemsParseError):
    def __init__(self, missing: set[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing required columns: {sorted(missing)}")


def _parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise OrderItemsParseError(f"Cannot parse date: {value!r}")


def _parse_decimal(value: str | None) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError as e:
        raise OrderItemsParseError(f"Cannot parse decimal: {value!r}") from e


def _parse_int(value: str | None) -> int:
    value = (value or "").strip()
    if not value:
        return 0
    try:
        return int(value)
    except ValueError as e:
        raise OrderItemsParseError(f"Cannot parse integer: {value!r}") from e


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_order_items(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise OrderItemsParseError(f"File not found: {path}")

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise MissingColumnsError(missing)
        return [_normalize_row(row) for row in reader]


def _normalize_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "transaction_id": row["Transaction ID"].strip(),
        "order_id": row["Order ID"].strip(),
        "sale_date": _parse_date(row["Sale Date"]),
        "listing_id": row["Listing ID"].strip(),
        "item_name": _clean(row.get("Item Name")),
        "quantity": _parse_int(row["Quantity"]),
        "price": _parse_decimal(row["Price"]),
        "item_total": _parse_decimal(row["Item Total"]),
        "currency": row["Currency"].strip(),
        "sku": _clean(row.get("SKU")),
    }