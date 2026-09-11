"""Tests for src/importer/service.py."""

import shutil
from pathlib import Path

import pytest

from src.database.connection import connect_and_init
from src.database.repositories import imports_repo, issues_repo, orders_repo
from src.importer import service


FIXTURE = Path(__file__).parent / "fixtures" / "EtsySoldOrders_sample.csv"


@pytest.fixture()
def conn(tmp_path: Path):
    connection = connect_and_init(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """Copy the fixture so tests can't accidentally overwrite it."""
    dst = tmp_path / "EtsySoldOrders_test.csv"
    shutil.copy(FIXTURE, dst)
    return dst


def test_detect_file_type() -> None:
    assert service.detect_file_type("EtsySoldOrders2026.csv") == "orders"
    assert service.detect_file_type("EtsySoldOrderItems2026.csv") == "order_items"
    assert service.detect_file_type("EtsyDeposits2026.csv") == "deposits"
    assert service.detect_file_type("random.csv") is None


def test_compute_file_hash_is_stable(sample_csv: Path) -> None:
    h1 = service.compute_file_hash(sample_csv)
    h2 = service.compute_file_hash(sample_csv)
    assert h1 == h2
    assert len(h1) == 64


def test_import_file_happy_path(conn, sample_csv: Path) -> None:
    result = service.import_file(conn, sample_csv)
    assert result.status == "SUCCESS"
    assert result.rows_total > 0
    assert result.rows_inserted == result.rows_total
    assert result.rows_skipped == 0
    assert result.already_imported is False
    assert orders_repo.count_orders(conn) == result.rows_total


def test_import_same_file_twice_is_skipped(conn, sample_csv: Path) -> None:
    first = service.import_file(conn, sample_csv)
    second = service.import_file(conn, sample_csv)
    assert second.already_imported is True
    assert second.import_id == first.import_id
    assert orders_repo.count_orders(conn) == first.rows_total


def test_missing_file_raises(conn, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        service.import_file(conn, tmp_path / "missing.csv")


def test_unknown_type_raises(conn, tmp_path: Path) -> None:
    bad = tmp_path / "unknown.csv"
    bad.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        service.import_file(conn, bad)


def test_unsupported_type_raises(conn, tmp_path: Path) -> None:
    other = tmp_path / "EtsyDeposits2026.csv"
    other.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        service.import_file(conn, other)


def test_parse_error_is_logged(conn, tmp_path: Path) -> None:
    """A malformed orders CSV must produce a FAILED import + ERROR issue."""
    bad = tmp_path / "EtsySoldOrders_broken.csv"
    bad.write_text('"Foo","Bar"\n1,2\n', encoding="utf-8")

    result = service.import_file(conn, bad)
    assert result.status == "FAILED"
    assert result.rows_total == 0

    issues = issues_repo.issues_for_import(conn, result.import_id)
    assert len(issues) == 1
    assert issues[0]["severity"] == "ERROR"
    assert issues[0]["check_name"] == "parse_error"


def test_duplicate_rows_are_logged(conn, tmp_path: Path) -> None:
    """Rows with duplicate order_id within one file are skipped + logged."""
    header = (
        '"Sale Date","Order ID","Currency","Order Value","Discount Amount",'
        '"Order Total","Card Processing Fees","Order Net"\n'
    )
    body = (
        '01/01/26,111,USD,6.99,0,6.99,0.46,6.53\n'
        '01/01/26,111,USD,6.99,0,6.99,0.46,6.53\n'
        '01/02/26,222,USD,6.99,0,6.99,0.46,6.53\n'
    )
    path = tmp_path / "EtsySoldOrders_dups.csv"
    path.write_text(header + body, encoding="utf-8")

    result = service.import_file(conn, path)
    assert result.rows_total == 3
    assert result.rows_inserted == 2
    assert result.rows_skipped == 1
    assert result.status == "SUCCESS_WITH_WARNINGS"

    issues = issues_repo.issues_for_import(conn, result.import_id)
    assert any(i["check_name"] == "duplicate_order_id" for i in issues)