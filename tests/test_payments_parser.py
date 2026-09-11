"""Tests for src/importer/parsers/payments.py."""

from pathlib import Path

import pytest

from src.importer.parsers.payments import (
    MissingColumnsError,
    PaymentsParseError,
    parse_payments,
)


HEADER = (
    '"Payment ID","Order ID","Gross Amount","Fees","Net Amount",'
    '"Refund Amount","Currency","Status","Funds Available","Order Date"\n'
)
ROW1 = '111,1001,6.99,0.46,6.53,0.00,USD,SETTLED,01/02/2026,01/01/2026\n'
ROW2 = '222,1002,5.24,0.41,4.83,0.00,USD,SETTLED,01/03/2026,01/02/2026\n'


def test_parses_valid_file(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text(HEADER + ROW1 + ROW2, encoding="utf-8")
    rows = parse_payments(p)
    assert len(rows) == 2
    assert rows[0]["payment_id"] == "111"
    assert rows[0]["gross_amount"] == 6.99
    assert rows[0]["net_amount"] == 6.53
    assert rows[0]["order_date"] == "2026-01-01"
    assert rows[0]["funds_available"] == "2026-01-02"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(PaymentsParseError):
        parse_payments(tmp_path / "nope.csv")


def test_missing_columns_raises(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text('"Payment ID","Order ID"\n1,2\n', encoding="utf-8")
    with pytest.raises(MissingColumnsError):
        parse_payments(p)


def test_invalid_date_raises(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text(HEADER + "1,2,3,4,5,0,USD,,,nope\n", encoding="utf-8")
    with pytest.raises(PaymentsParseError):
        parse_payments(p)