"""Parser for EtsyDirectCheckoutPayments*.csv files.

This is the financial ledger. Revenue, fees, and refunds all come
from here. Only the columns needed for MVP analytics are extracted.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "Payment ID",
    "Order ID",
    "Gross Amount",
    "Fees",
    "Net Amount",
    "Currency",
    "Order Date",
})


class PaymentsParseError(Exception):
    """Raised when a payments CSV cannot be parsed."""


class MissingColumnsError(PaymentsParseError):
    def __init__(self, missing: set[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing required columns: {sorted(missing)}")


def _parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise PaymentsParseError(f"Cannot parse date: {value!r}")


def _parse_decimal(value: str | None) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError as e:
        raise PaymentsParseError(f"Cannot parse decimal: {value!r}") from e


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_payments(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise PaymentsParseError(f"File not found: {path}")

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise MissingColumnsError(missing)
        return [_normalize_row(row) for row in reader]


def _normalize_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "payment_id": row["Payment ID"].strip(),
        "order_id": row["Order ID"].strip(),
        "gross_amount": _parse_decimal(row["Gross Amount"]),
        "fees": _parse_decimal(row["Fees"]),
        "net_amount": _parse_decimal(row["Net Amount"]),
        "refund_amount": _parse_decimal(row.get("Refund Amount")),
        "currency": row["Currency"].strip(),
        "order_date": _parse_date(row["Order Date"]),
        "funds_available": _parse_date(row.get("Funds Available", "")),
        "status": _clean(row.get("Status")),
    }