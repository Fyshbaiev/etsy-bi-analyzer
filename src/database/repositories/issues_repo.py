"""Repository for the `data_quality_issues` table.

Every validation or reconciliation finding is stored here. Severity
must be one of INFO, WARNING, ERROR (enforced by the schema).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any


VALID_SEVERITIES = {"INFO", "WARNING", "ERROR"}


def add_issue(
    conn: sqlite3.Connection,
    check_name: str,
    severity: str,
    message: str,
    *,
    import_id: int | None = None,
    table_name: str | None = None,
    row_ref: str | None = None,
    field_name: str | None = None,
) -> int:
    """Record one issue. Returns issue_id."""
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity: {severity!r}")

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO data_quality_issues
            (import_id, check_name, severity, table_name,
             row_ref, field_name, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (import_id, check_name, severity, table_name,
         row_ref, field_name, message, created_at),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_issues(
    conn: sqlite3.Connection,
    severity: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return issues, optionally filtered by severity."""
    if severity:
        rows = conn.execute(
            """
            SELECT * FROM data_quality_issues
            WHERE severity = ?
            ORDER BY created_at DESC, issue_id DESC
            LIMIT ?
            """,
            (severity, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM data_quality_issues
            ORDER BY created_at DESC, issue_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_by_severity(conn: sqlite3.Connection) -> dict[str, int]:
    """Return {'INFO': n, 'WARNING': n, 'ERROR': n}."""
    result = {s: 0 for s in VALID_SEVERITIES}
    rows = conn.execute(
        "SELECT severity, COUNT(*) FROM data_quality_issues GROUP BY severity"
    ).fetchall()
    for sev, count in rows:
        result[sev] = int(count)
    return result


def issues_for_import(
    conn: sqlite3.Connection, import_id: int
) -> list[dict[str, Any]]:
    """Return all issues for a specific import."""
    rows = conn.execute(
        """
        SELECT * FROM data_quality_issues
        WHERE import_id = ?
        ORDER BY issue_id
        """,
        (import_id,),
    ).fetchall()
    return [dict(r) for r in rows]