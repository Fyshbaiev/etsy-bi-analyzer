# Architecture

This document describes the high-level architecture of Etsy BI Analyzer:
layers, responsibilities, data flow, and folder structure.

## Overview

Etsy BI Analyzer is a standalone Windows desktop application. It has no
server, no cloud component, and no network calls at runtime. All data
stays on the user's machine.

Data flow:
CSV files (Etsy exports)
     │
     ▼
┌─────────┐
│ Importer│ parse, validate, normalize
└────┬────┘
     │
     ▼
┌──────────┐
│ SQLite DB│ persistent storage
└────┬─────┘
     │
     ▼
┌───────────┐
│ Analytics │ compute metrics
└────┬──────┘
     │
     ├──────────────┐
     ▼              ▼
┌──────────┐   ┌──────────┐
│ Insights │   │ Reports  │
│ rules    │   │ Excel    │
└────┬─────┘   └────┬─────┘
     │              │
     └──────┬───────┘
            ▼
┌─────────────┐
│ PySide6 UI  │
└─────────────┘

## Layers

The application is split into six layers. Each layer has a clear
responsibility and depends only on the layers below it.

### 1. UI layer (`src/app/`)

- PySide6 widgets, windows, and pages.
- Reads data from Analytics and Reports.
- Triggers Importer on user action.
- **Does not** contain business logic.
- **Does not** touch SQLite directly.

### 2. Analytics layer (`src/analytics/`)

- Calculates KPIs, product metrics, financials, geography, refunds.
- Reads from the database through repositories.
- Returns plain Python objects (dataclasses, dicts, DataFrames).
- **Does not** import PySide6.

### 3. Insights layer (`src/insights/`)

- Rule engine that turns metrics into human-readable observations.
- Pure functions on metric inputs.
- **Does not** import PySide6.

### 4. Reports layer (`src/reports/`)

- Generates Excel reports from metrics.
- Uses `openpyxl`.
- **Does not** import PySide6.

### 5. Importer layer (`src/importer/`)

- Reads CSV files, detects their type, validates them.
- Parses each file type into a normalized structure.
- Writes to the database through repositories.
- Records data quality issues.
- **Does not** import PySide6.
- **Does not** compute business metrics.

### 6. Database layer (`src/database/`)

- Owns the SQLite schema.
- Provides connection management.
- Provides repository classes for each table.
- **Does not** import PySide6.
- **Does not** know about CSV files.

Cross-cutting concerns live in `src/core/`:

- `config.py` — application configuration (paths, defaults).
- `paths.py` — resolves `%APPDATA%\EtsyBIAnalyzer\` and subfolders.
- `logging.py` — logging setup.

## Folder structure
etsy-bi-analyzer/
├── src/
│ ├── app/ # PySide6 UI
│ ├── core/ # config, paths, logging
│ ├── importer/ # CSV parsing and validation
│ ├── database/ # SQLite schema and repositories
│ ├── analytics/ # metric calculations
│ ├── insights/ # rule engine
│ └── reports/ # Excel generation
├── tests/ # pytest
├── docs/ # documentation
├── sample_data/ # anonymized sample CSVs
├── assets/ # icons, images
├── scripts/ # dev helper scripts
├── pyproject.toml
└── README.md

## Dependency rules

The following rules are enforced by design and should be respected in
every pull request:

| Layer | May import from |
|---|---|
| `app` | `core`, `analytics`, `insights`, `reports`, `importer`, `database` |
| `analytics` | `core`, `database` |
| `insights` | `core`, `analytics` |
| `reports` | `core`, `analytics` |
| `importer` | `core`, `database` |
| `database` | `core` |
| `core` | nothing (only standard library and third-party packages) |

**Rule:** no layer imports from a layer above it. Only `app` may import
from everything, and only `app` may import PySide6.

## Storage

### Where data lives

Runtime data is stored **outside** the project folder, in the user's
`%APPDATA%` directory:
%APPDATA%\EtsyBIAnalyzer
├── config.json # user settings
├── data.db # SQLite database
├── imports/ # copies of imported CSV files
└── logs/
└── app.log

Rationale: the application is installed as a `.exe`, and the folder
that contains the `.exe` may be read-only. Writing to `%APPDATA%` is
the standard Windows convention.

### What is not stored

- No user credentials.
- No Etsy API tokens.
- No telemetry.
- No cloud sync.

## Threading

CSV import and Excel export are the two slowest operations. Both run
in a background thread to keep the UI responsive.

- UI runs on the main thread (Qt requirement).
- Import and export run on `QThread`.
- Progress is reported back via Qt signals.
- The database connection is opened per thread.

## Error handling

- Errors during import are recorded as `data_quality_issues`.
- Fatal errors (unreadable file, corrupted database) show a modal
  dialog and log to `app.log`.
- The application never crashes silently.

## Packaging

The application is packaged with **PyInstaller** in `--onedir` mode.

- Result: `dist/EtsyBIAnalyzer/EtsyBIAnalyzer.exe` plus support files.
- User receives either the whole folder or an installer (Phase 2).
- Build instructions live in `docs/build.md`.

## What is out of scope

The following are explicitly excluded from the current architecture:

- Web UI, browser access.
- Multi-user mode.
- Cloud storage or synchronization.
- Etsy API integration.
- Automatic background imports.
- Multi-currency support.
- Plugin system.