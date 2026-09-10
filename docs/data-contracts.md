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

  
---

## 2. Order Items

**Source file pattern:** `EtsySoldOrderItems*.csv`
**Export location:** Etsy Shop Manager → Orders → Download CSV
**Row meaning:** one line item. An order with three items produces three rows.

### Required columns

| Column | Type | Notes |
|---|---|---|
| `Sale Date` | date | Format `MM/DD/YY` |
| `Order ID` | string | Foreign key to `SoldOrders` |
| `Transaction ID` | string | Unique per line item |
| `Listing ID` | string | Identifier of the sold listing |
| `Item Name` | string | Listing title at the moment of sale |
| `Quantity` | integer | Units sold in this line |
| `Price` | decimal | Unit price |
| `Item Total` | decimal | `Price × Quantity`, before discount |
| `Currency` | string | ISO code, e.g. `USD` |

### Optional columns

`Buyer`, `Coupon Code`, `Coupon Details`, `Discount Amount`,
`Shipping Discount`, `Order Shipping`, `Order Sales Tax`, `Date Paid`,
`Date Shipped`, `Ship Name`, `Ship Address1`, `Ship Address2`,
`Ship City`, `Ship State`, `Ship Zipcode`, `Ship Country`,
`Variations`, `Order Type`, `Listings Type`, `Payment Type`,
`InPerson Discount`, `InPerson Location`, `VAT Paid by Buyer`, `SKU`.

### Validation rules

- `Order ID` must be non-empty and must exist in `SoldOrders`.
  Orphan rows are recorded as data quality issues.
- `Transaction ID` must be non-empty and unique across all imports.
- `Listing ID` must be non-empty.
- `Quantity` must be a positive integer.
- `Price`, `Item Total` must parse as decimals.
- `Item Total` should equal `Price × Quantity`. A mismatch is a warning.
- `SKU` is often empty; do not rely on it.
- Multiple rows with the same `Order ID` are expected and valid
  (one row per line item).

### Notes

- This is the **only file** in the Etsy export set that contains both
  `Order ID` and `Listing ID` together. All product-level analytics
  (Top Products, ABC, revenue by listing) depend on this file.
- The catalog file `EtsyListingsDownload*.csv` does **not** contain a
  `Listing ID` column, so a direct join between catalog and sales is not
  possible. This is a known limitation.
- `Discount Amount` on this row is the per-line discount. It is separate
  from the order-level discount in `SoldOrders`.