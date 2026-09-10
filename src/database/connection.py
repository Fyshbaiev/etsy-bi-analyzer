"""SQLite connection helper.

This is the only place in the codebase that opens a database
connection. All repositories receive a connection from here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults.

    - Row factory is set to sqlite3.Row so results behave like dicts.
    - Foreign keys are enabled (SQLite has them off by default).
    - Parent directory is created if it does not exist.
    """
    if isinstance(db_path, Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Apply the schema to the given connection."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def connect_and_init(db_path: Path | str) -> sqlite3.Connection:
    """Connect and make sure the schema is applied."""
    conn = connect(db_path)
    init_schema(conn)
    return conn