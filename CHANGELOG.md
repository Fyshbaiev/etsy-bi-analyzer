# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-14

### Added

- CSV import for three Etsy export types: sold orders, order items,
  direct checkout payments.
- SQLite storage with a normalized schema for orders, order items,
  payments, deposits, listings, imports, and data quality issues.
- Data validation and normalization for every parsed field.
- Import service with file hashing for duplicate detection.
- KPI module: gross/net revenue, fees, refunds, AOV, AIV, fee ratio,
  refund rate, items per order.
- Reconciliation module: 10 cross-table checks with severity levels.
- Rule-based insights engine.
- Excel report with six sheets.
- PySide6 desktop UI with six tabs: Dashboard, Sales, Products,
  Countries, Data Quality, Insights.
- PyInstaller build with a spec file, version info, and repeatable
  build script.
- 97 automated tests covering parsers, repositories, analytics,
  insights, reports, and UI.
- Documentation: data contracts, metric definitions, reconciliation
  spec, architecture overview, build guide, and three ADRs.

[0.1.0]: https://github.com/Fyshbaiev/etsy-bi-analyzer/releases/tag/v0.1.0