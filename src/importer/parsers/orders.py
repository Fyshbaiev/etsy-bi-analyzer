"""Parser for EtsySoldOrders*.csv files.

Reads a sold orders CSV, validates that the required columns are
present, and returns normalized rows.

The parser does not touch the database. It only reads and normalizes.
Extended columns (name, address, coupon, etc.) will be added later.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


# Only these columns are required for the first iteration.
REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "Sale Date",
    "Order ID",
    "Currency",
    "Order Value",
    "Discount Amount",
    "Order Total",
    "Card Processing Fees",
    "Order Net",
})


class OrdersParseError(Exception):
    """Raised when a sold orders CSV cannot be parsed."""


class MissingColumnsError(OrdersParseError):
    """Raised when one or more required columns are missing."""

    def __init__(self, missing: set[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing required columns: {sorted(missing)}")


def _parse_date(value: str) -> str | None:
    """Parse MM/DD/YY or MM/DD/YYYY into an ISO date string."""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise OrdersParseError(f"Cannot parse date: {value!r}")


def _parse_decimal(value: str | None) -> float:
    """Parse a decimal string. Empty or None becomes 0.0."""
    value = (value or "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError as e:
        raise OrdersParseError(f"Cannot parse decimal: {value!r}") from e


def parse_orders(path: Path | str) -> list[dict[str, Any]]:
    """Parse a sold orders CSV file into a list of normalized dicts.

    Only the required columns are returned for now. The remaining
    columns will be added in a later step.

    Raises:
        OrdersParseError: if the file is missing or contains unparsable values.
        MissingColumnsError: if required columns are absent.
    """
    path = Path(path)
    if not path.exists():
        raise OrdersParseError(f"File not found: {path}")

    # utf-8-sig strips the UTF-8 BOM that Etsy puts at the start of every export.
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise MissingColumnsError(missing)
        return [_normalize_row(row) for row in reader]


def _normalize_row(row: dict[str, str]) -> dict[str, Any]:
    """Convert one raw CSV row into a dict with typed values."""
    return {
        "order_id": row["Order ID"].strip(),
        "sale_date": _parse_date(row["Sale Date"]),
        "currency": row["Currency"].strip(),
        "order_value": _parse_decimal(row["Order Value"]),
        "discount_amount": _parse_decimal(row["Discount Amount"]),
        "order_total": _parse_decimal(row["Order Total"]),
        "card_processing_fees": _parse_decimal(row["Card Processing Fees"]),
        "order_net": _parse_decimal(row["Order Net"]),
    }