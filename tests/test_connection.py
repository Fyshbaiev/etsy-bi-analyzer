"""Tests for src/database/connection.py."""

from pathlib import Path

from src.database.connection import connect_and_init


EXPECTED_TABLES = {
    "imports",
    "orders",
    "order_items",
    "payments",
    "deposits",
    "listings_catalog",
    "data_quality_issues",
}


def test_connect_and_init_creates_all_tables(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = connect_and_init(db)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        tables = {row["name"] for row in rows}
        assert EXPECTED_TABLES.issubset(tables)
    finally:
        conn.close()


def test_foreign_keys_are_enabled(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = connect_and_init(db)
    try:
        value = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert value == 1
    finally:
        conn.close()


def test_row_factory_returns_named_rows(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = connect_and_init(db)
    try:
        row = conn.execute("SELECT 1 AS value").fetchone()
        assert row["value"] == 1
    finally:
        conn.close()