# Data Contracts

This document describes every CSV file that the Etsy BI Analyzer expects
as input, along with its required columns, data types, and validation rules.

The importer relies on this document as the source of truth for parsing and
validation. Any change to the input format must be reflected here first.

## Supported sources

| # | File | Purpose |
|---|------|---------|
| 1 | `EtsySoldOrders*.csv` | One row per order |
| 2 | `EtsySoldOrderItems*.csv` | One row per item in an order |
| 3 | `EtsyDirectCheckoutPayments*.csv` | Payment ledger per order |
| 4 | `EtsyDeposits*.csv` | Bank payout history |
| 5 | `EtsyListingsDownload*.csv` | Catalog of listings |

---

## 1. Sold Orders

**Source file pattern:** `EtsySoldOrders*.csv`
**Export location:** Etsy Shop Manager → Orders → Download CSV
**Row meaning:** one order.

### Required columns

| Column | Type | Notes |
|---|---|---|
| `Sale Date` | date | Format `MM/DD/YY` (e.g. `09/06/26`) |
| `Order ID` | string | Unique per order |
| `Buyer User ID` | string | May be empty for guest accounts |
| `Full Name` | string | Buyer's full name |
| `Currency` | string | ISO code, e.g. `USD` |
| `Order Value` | decimal | Gross amount before discount |
| `Discount Amount` | decimal | Total discount applied |
| `Order Total` | decimal | Amount the buyer saw at checkout |
| `Card Processing Fees` | decimal | Payment processing fees |
| `Order Net` | decimal | What the shop receives |
| `Ship Country` | string | Destination country |

### Optional columns

`First Name`, `Last Name`, `Number of Items`, `Payment Method`,
`Date Shipped`, `Street 1`, `Street 2`, `Ship City`, `Ship State`,
`Ship Zipcode`, `Coupon Code`, `Coupon Details`, `Shipping Discount`,
`Shipping`, `Sales Tax`, `Status`, `Adjusted Order Total`,
`Adjusted Card Processing Fees`, `Adjusted Net Order Amount`,
`Buyer`, `Order Type`, `Payment Type`, `InPerson Discount`,
`InPerson Location`, `SKU`.

### Validation rules

- `Order ID` must be non-empty and unique.
- `Sale Date` must parse as a date.
- `Currency` must be `USD` in the current MVP (multi-currency is out of scope).
- `Order Value`, `Discount Amount`, `Order Total`, `Card Processing Fees`, `Order Net`
  must parse as decimals.
- `Status` is often empty in real exports; do not rely on it for filtering.
- The following identity is **not** guaranteed by the source data and must be checked
  during validation:
  `Order Value − Discount Amount == Order Total`.
  Real exports show discrepancies (VAT presentation, rounding), so a mismatch
  should produce a warning, not an error.

### Notes

- `Order ID` is the foreign key used everywhere else in the system
  (`Order Items`, `Payments`).
- `Card Processing Fees` and `Order Net` must match the corresponding values
  in `EtsyDirectCheckoutPayments*.csv` for the same `Order ID`.
  Any mismatch is recorded as a data quality issue.
- The column `Status` is present but frequently empty. Refunds are detected
  from the `Payments` file, not from this column.