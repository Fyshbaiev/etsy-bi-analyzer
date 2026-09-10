# Etsy BI Analyzer

A desktop application that turns Etsy Shop Manager CSV exports into a business report.

> **Status:** in early development. Not usable yet.

## What it does

- Imports Etsy CSV exports (orders, order items, payments, deposits, listings)
- Validates and cleans the data
- Stores everything in a local SQLite database
- Calculates KPIs, financials, and product analytics
- Generates an Excel report and rule-based insights

## What it does NOT do

- No Etsy API integration
- No cloud, no accounts, no telemetry
- No profit calculation (COGS is unknown)
- No per-product fee attribution

## Stack

- Python 3.12
- PySide6 (Qt for Python)
- SQLite
- pandas
- openpyxl
- PyInstaller for packaging

## Status

Early development. The project is being built step by step.

## License

MIT — see [LICENSE](LICENSE).