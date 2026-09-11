"""Tests for src/database/repositories/issues_repo.py."""

from pathlib import Path

import pytest

from src.database.connection import connect_and_init
from src.database.repositories import imports_repo, issues_repo


@pytest.fixture()
def conn(tmp_path: Path):
    connection = connect_and_init(tmp_path / "test.db")
    yield connection
    connection.close()


def test_add_and_list_issue(conn) -> None:
    issues_repo.add_issue(
        conn,
        check_name="parse_error",
        severity="ERROR",
        message="missing column",
        table_name="orders",
    )
    all_issues = issues_repo.list_issues(conn)
    assert len(all_issues) == 1
    assert all_issues[0]["check_name"] == "parse_error"
    assert all_issues[0]["severity"] == "ERROR"


def test_invalid_severity_raises(conn) -> None:
    with pytest.raises(ValueError):
        issues_repo.add_issue(conn, "x", "BROKEN", "msg")


def test_count_by_severity(conn) -> None:
    issues_repo.add_issue(conn, "a", "INFO", "i")
    issues_repo.add_issue(conn, "b", "WARNING", "w1")
    issues_repo.add_issue(conn, "c", "WARNING", "w2")
    issues_repo.add_issue(conn, "d", "ERROR", "e")
    counts = issues_repo.count_by_severity(conn)
    assert counts == {"INFO": 1, "WARNING": 2, "ERROR": 1}


def test_issues_for_import_filters(conn) -> None:
    import_id = imports_repo.create_import(conn, "a.csv", "orders", "h")
    issues_repo.add_issue(conn, "x", "INFO", "m1", import_id=import_id)
    issues_repo.add_issue(conn, "y", "ERROR", "m2", import_id=import_id)
    issues_repo.add_issue(conn, "z", "INFO", "m3")  # no import_id
    found = issues_repo.issues_for_import(conn, import_id)
    assert len(found) == 2