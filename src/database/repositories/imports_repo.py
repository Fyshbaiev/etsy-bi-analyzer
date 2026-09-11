"""Repository for the `imports` table.

Every CSV import gets one row here. The row records the file name,
type, SHA-256 hash, and statistics. The file_hash column is UNIQUE,
so re-importing the same file is rejected at the database level.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any


def get_import_by_hash(
    conn: sqlite3.Connection, file_hash: str
) -> dict[str, Any] | None:
    """Return the import record for the given file hash, or None."""
    row = conn.execute(
        "SELECT * FROM imports WHERE file_hash = ?", (file_hash,)
    ).fetchone()
    return dict(row) if row else None


def create_import(
    conn: sqlite3.Connection,
    filename: str,
    file_type: str,
    file_hash: str,
) -> int:
    """Insert a new import record in PENDING status. Returns import_id."""
    import_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO imports (filename, file_type, file_hash, import_date, status)
        VALUES (?, ?, ?, ?, 'PENDING')
        """,
        (filename, file_type, file_hash, import_date),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_import_stats(
    conn: sqlite3.Connection,
    import_id: int,
    rows_total: int,
    rows_valid: int,
    rows_invalid: int,
    status: str,
) -> None:
    """Update statistics for a finished import."""
    conn.execute(
        """
        UPDATE imports
        SET rows_total = ?, rows_valid = ?, rows_invalid = ?, status = ?
        WHERE import_id = ?
        """,
        (rows_total, rows_valid, rows_invalid, status, import_id),
    )
    conn.commit()


def list_imports(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all import records, newest first."""
    rows = conn.execute(
        "SELECT * FROM imports ORDER BY import_date DESC"
    ).fetchall()
    return [dict(r) for r in rows]