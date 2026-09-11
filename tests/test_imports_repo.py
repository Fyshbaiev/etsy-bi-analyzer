"""Tests for src/database/repositories/imports_repo.py."""

from pathlib import Path

import pytest

from src.database.connection import connect_and_init
from src.database.repositories import imports_repo


@pytest.fixture()
def conn(tmp_path: Path):
    connection = connect_and_init(tmp_path / "test.db")
    yield connection
    connection.close()


def test_get_by_hash_returns_none_when_missing(conn) -> None:
    assert imports_repo.get_import_by_hash(conn, "deadbeef") is None


def test_create_and_get_by_hash(conn) -> None:
    import_id = imports_repo.create_import(
        conn, "orders.csv", "orders", "hash-001"
    )
    assert import_id > 0

    found = imports_repo.get_import_by_hash(conn, "hash-001")
    assert found is not None
    assert found["filename"] == "orders.csv"
    assert found["file_type"] == "orders"
    assert found["status"] == "PENDING"
    assert found["rows_total"] == 0


def test_duplicate_hash_is_rejected(conn) -> None:
    imports_repo.create_import(conn, "a.csv", "orders", "hash-dup")
    with pytest.raises(Exception):
        imports_repo.create_import(conn, "b.csv", "orders", "hash-dup")


def test_update_stats(conn) -> None:
    import_id = imports_repo.create_import(
        conn, "orders.csv", "orders", "hash-002"
    )
    imports_repo.update_import_stats(
        conn,
        import_id,
        rows_total=100,
        rows_valid=95,
        rows_invalid=5,
        status="SUCCESS",
    )
    rec = imports_repo.get_import_by_hash(conn, "hash-002")
    assert rec is not None
    assert rec["rows_total"] == 100
    assert rec["rows_valid"] == 95
    assert rec["rows_invalid"] == 5
    assert rec["status"] == "SUCCESS"


def test_list_imports_returns_records(conn) -> None:
    imports_repo.create_import(conn, "a.csv", "orders", "h-a")
    imports_repo.create_import(conn, "b.csv", "payments", "h-b")
    result = imports_repo.list_imports(conn)
    assert len(result) == 2
    types = {r["file_type"] for r in result}
    assert types == {"orders", "payments"}