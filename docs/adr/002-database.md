# ADR-002: Database engine — SQLite

**Date:** 2026-09-10
**Status:** Accepted

## Context

The application needs a local database to store imported Etsy data.
Requirements:

- runs on Windows without installation,
- single-file storage that the user can back up or delete,
- works fully offline,
- supports standard SQL (joins, aggregates, indexes),
- integrates with Python without a server process,
- keeps the repository free of binary or user data.

Candidate options:

| Option | Pros | Cons |
|---|---|---|
| **SQLite** | Zero setup, single file, bundled with Python, standard SQL | Limited concurrency, not designed for huge datasets |
| **DuckDB** | Fast analytics, columnar storage, single file | Less ubiquitous, still evolving |
| **PostgreSQL** | Production-grade, strong SQL | Requires installation and a running service |
| **Files (CSV / Parquet)** | Simplest possible | No joins, no constraints, weak query support |

## Decision

Use **SQLite** as the only persistent store for the application.

The database lives in the user's `%APPDATA%\EtsyBIAnalyzer\data.db`.
It is **never** stored inside the project folder or the Git repository.

## Consequences

**Positive:**

- The `sqlite3` module is part of Python's standard library — no extra
  dependency, no installation step for the user.
- The database is a single file. Backup and reset are trivial.
- Standard SQL is used everywhere, which is directly transferable
  knowledge and looks good on a portfolio.
- Data quality issues can be stored in the same file as imported data.
- Tests can use an in-memory database (`:memory:`) for speed.

**Negative:**

- SQLite has limited write concurrency. This is acceptable because
  the application is single-user and imports are sequential.
- Very large datasets (tens of millions of rows) may become slow.
  This is not expected for a small Etsy shop.
- The `DATE` and `BOOLEAN` types are stored as text and integers
  respectively; parsing must be done in Python.

## Alternatives reconsidered

**DuckDB** was a serious candidate because of its columnar engine and
excellent performance for analytical queries. It was rejected because:

- it introduces a second query engine in a Python-first project,
- it is less common in job descriptions than SQLite,
- the analytical workloads here (thousands to hundreds of thousands of
  rows) do not need a columnar engine.

**PostgreSQL** was rejected because the user should not have to install
and manage a database server to use a desktop tool.

**Plain files** were rejected because the project needs joins, foreign
keys, indexes, and constraint checks. Doing this in Python would
reinvent a database badly.

## Notes

- Migrations will be handled by versioned SQL scripts in
  `src/database/migrations/`, applied in order at application start.
- The schema lives in `src/database/schema.sql` as the canonical
  definition.
- Every repository module in `src/database/repositories/` maps to one
  or more tables and is the only place that issues SQL for those tables.