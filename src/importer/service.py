"""Import service.

Ties together: file hash check → import record → parser → repository
→ data quality logging. This is the entry point the UI will call.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.database.repositories import imports_repo, issues_repo, orders_repo
from src.importer.parsers.orders import (
    OrdersParseError,
    parse_orders,
)


# Filename patterns → internal file type. Order matters: more specific
# patterns must be listed before more general ones.
_FILENAME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^EtsySoldOrderItems.*\.csv$", re.IGNORECASE), "order_items"),
    (re.compile(r"^EtsySoldOrders.*\.csv$", re.IGNORECASE), "orders"),
    (re.compile(r"^EtsyDirectCheckoutPayments.*\.csv$", re.IGNORECASE), "payments"),
    (re.compile(r"^EtsyDeposits.*\.csv$", re.IGNORECASE), "deposits"),
    (re.compile(r"^EtsyListingsDownload.*\.csv$", re.IGNORECASE), "listings"),
]


# Which file types the service can currently process end to end.
SUPPORTED_TYPES: frozenset[str] = frozenset({"orders"})


@dataclass
class ImportResult:
    """Outcome of one import operation."""

    import_id: int | None
    file_type: str
    filename: str
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    status: str
    already_imported: bool = False


def compute_file_hash(path: Path | str) -> str:
    """Compute SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_file_type(filename: str) -> str | None:
    """Guess the Etsy file type from the filename.

    Returns one of: 'orders', 'order_items', 'payments', 'deposits',
    'listings'. Returns None if nothing matches.
    """
    name = Path(filename).name
    for pattern, kind in _FILENAME_PATTERNS:
        if pattern.match(name):
            return kind
    return None


def import_file(
    conn: sqlite3.Connection,
    path: Path | str,
    file_type: str | None = None,
) -> ImportResult:
    """Import a single CSV file into the database.

    Steps:
      1. Compute hash, check for duplicate import.
      2. Create import record.
      3. Parse file (per type).
      4. Insert rows, count inserted/skipped.
      5. Log any errors as data quality issues.
      6. Update import statistics.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file type is unknown or unsupported.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    resolved_type = file_type or detect_file_type(path.name)
    if resolved_type is None:
        raise ValueError(
            f"Cannot detect file type for {path.name!r}. "
            f"Pass file_type explicitly."
        )
    if resolved_type not in SUPPORTED_TYPES:
        raise ValueError(
            f"File type {resolved_type!r} is not yet supported. "
            f"Supported: {sorted(SUPPORTED_TYPES)}"
        )

    file_hash = compute_file_hash(path)
    existing = imports_repo.get_import_by_hash(conn, file_hash)
    if existing is not None:
        return ImportResult(
            import_id=existing["import_id"],
            file_type=existing["file_type"],
            filename=existing["filename"],
            rows_total=existing["rows_total"],
            rows_inserted=0,
            rows_skipped=0,
            status=existing["status"],
            already_imported=True,
        )

    import_id = imports_repo.create_import(
        conn, path.name, resolved_type, file_hash
    )

    try:
        rows = parse_orders(path)
    except OrdersParseError as e:
        issues_repo.add_issue(
            conn,
            check_name="parse_error",
            severity="ERROR",
            message=str(e),
            import_id=import_id,
            table_name="orders",
        )
        imports_repo.update_import_stats(
            conn, import_id, 0, 0, 0, "FAILED"
        )
        return ImportResult(
            import_id=import_id,
            file_type=resolved_type,
            filename=path.name,
            rows_total=0,
            rows_inserted=0,
            rows_skipped=0,
            status="FAILED",
        )

    rows_total = len(rows)
    rows_inserted = orders_repo.insert_orders(conn, rows, import_id)
    rows_skipped = rows_total - rows_inserted

    if rows_skipped > 0:
        issues_repo.add_issue(
            conn,
            check_name="duplicate_order_id",
            severity="INFO",
            message=f"{rows_skipped} rows skipped as duplicates.",
            import_id=import_id,
            table_name="orders",
        )

    status = "SUCCESS" if rows_skipped == 0 else "SUCCESS_WITH_WARNINGS"
    imports_repo.update_import_stats(
        conn,
        import_id,
        rows_total=rows_total,
        rows_valid=rows_inserted,
        rows_invalid=rows_skipped,
        status=status,
    )

    return ImportResult(
        import_id=import_id,
        file_type=resolved_type,
        filename=path.name,
        rows_total=rows_total,
        rows_inserted=rows_inserted,
        rows_skipped=rows_skipped,
        status=status,
    )