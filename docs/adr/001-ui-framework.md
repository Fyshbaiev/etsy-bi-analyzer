# ADR-001: UI framework — PySide6

**Date:** 2026-09-10
**Status:** Accepted

## Context

The application needs a desktop UI that can be packaged as a
standalone Windows `.exe`. Target users are shop owners who do not
have Python installed and will not install it. The UI must:

- run natively on Windows without a browser,
- include tables, forms, and charts suitable for a BI tool,
- be packageable into a single distributable folder,
- be maintainable by a single developer.

Several options were considered:

| Option | Pros | Cons |
|---|---|---|
| **Tkinter** | Bundled with Python, smallest `.exe` | Dated look, weak table widgets |
| **CustomTkinter** | Modern look on top of Tkinter | Smaller widget ecosystem, fewer table features |
| **PySide6 (Qt)** | Professional look, strong tables and charts, mature | Large `.exe` (~100 MB), more PyInstaller complexity |
| **Flet** | Python-native, decent packaging | Smaller community, weaker BI tables |
| **Electron / Tauri** | Web UI flexibility | Not Python; introduces a second language and toolchain |

## Decision

Use **PySide6** as the UI framework.

## Consequences

**Positive:**

- Native Windows look with minimal effort.
- `QTableView` with model-view pattern handles large datasets well.
- `QtCharts` provides line and bar charts without extra dependencies.
- The framework is mature, documented, and widely used.

**Negative:**

- The `.exe` will be around 100 MB.
- PyInstaller needs explicit flags (`--collect-all PySide6`).
- Antivirus software may flag the packaged executable; a code-signing
  certificate may be required for public distribution in Phase 2.
- Qt is licensed under LGPL. For a personal or portfolio project this
  is fine; commercial distribution would require compliance with LGPL
  terms.

## Alternatives reconsidered

CustomTkinter was a serious candidate for a faster MVP, but the
application needs data tables with sorting, filtering, and large row
counts. This is a core UI feature, not a nice-to-have. PySide6 was
chosen because it provides this out of the box.

Tkinter was rejected for the same reason.

Flet was rejected because of its smaller ecosystem for BI-style tables.

Electron and Tauri were rejected because they introduce a second
programming language and toolchain, which is out of scope for a
Python-first portfolio project.