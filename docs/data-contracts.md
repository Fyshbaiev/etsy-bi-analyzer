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

  
---

## 3. Direct Checkout Payments

**Source file pattern:** `EtsyDirectCheckoutPayments*.csv`
**Export location:** Etsy Shop Manager → Finances → Payment account → Download CSV
**Row meaning:** one payment record per order. This is the financial ledger.

### Required columns

| Column | Type | Notes |
|---|---|---|
| `Payment ID` | string | Unique per payment record |
| `Order ID` | string | Foreign key to `SoldOrders` |
| `Gross Amount` | decimal | Amount charged before fees |
| `Fees` | decimal | Total fees kept by Etsy (transaction + processing) |
| `Net Amount` | decimal | Amount credited to the shop |
| `Refund Amount` | decimal | Amount refunded to the buyer |
| `Currency` | string | ISO code, e.g. `USD` |
| `Status` | string | e.g. `SETTLED` |
| `Funds Available` | date | Date when funds become available for payout |
| `Order Date` | date | Date of the original order |

### Optional columns

`Buyer Username`, `Buyer Name`, `Posted Gross`, `Posted Fees`,
`Posted Net`, `Adjusted Gross`, `Adjusted Fees`, `Adjusted Net`,
`Listing Amount`, `Listing Currency`, `Exchange Rate`,
`VAT Amount`, `Gift Card Applied?`, `Buyer`, `Order Type`,
`Payment Type`.

### Validation rules

- `Payment ID` must be non-empty and unique.
- `Order ID` must be non-empty and exist in `SoldOrders`.
  Orphans are recorded as data quality issues.
- `Gross Amount`, `Fees`, `Net Amount`, `Refund Amount` must parse as decimals.
- The following identity must hold for every row:
  `Gross Amount − Fees = Net Amount`.
  A mismatch is an error.
- `Refund Amount` is usually `0`. A non-zero value indicates a refund.
- `Status` is expected to be `SETTLED` for completed transactions.
  Other values should be logged but not treated as errors in the MVP.

### Notes

- This file is the **only authoritative source** for fees, net amounts,
  and refunds. `SoldOrders.Card Processing Fees` and `SoldOrders.Order Net`
  must match the corresponding values here for the same `Order ID`.
- `Gross Amount` is the amount charged to the buyer *after* discounts.
  It corresponds to `SoldOrders.Order Value − SoldOrders.Discount Amount`.
- `Listing Amount` and `Order Total` in other files are buyer-facing amounts
  that may include VAT or currency presentation. They are **not** used for
  revenue calculations.
- Fee attribution per product is not possible from this file: fees are
  recorded at the order level, not at the line-item level.

  
---

## 4. Deposits

**Source file pattern:** `EtsyDeposits*.csv`
**Export location:** Etsy Shop Manager → Finances → Deposits → Download CSV
**Row meaning:** one payout from Etsy to the shop's bank account.

### Required columns

| Column | Type | Notes |
|---|---|---|
| `Date` | date | Payout date, format `Month D, YYYY` (e.g. `January 5, 2026`) |
| `Amount` | decimal | Amount transferred to the bank account |
| `Currency` | string | ISO code, e.g. `USD` |
| `Status` | string | e.g. `Executed` |
| `Bank Account Ending Digits` | string | Last 4 digits of the receiving account |

### Validation rules

- `Date` must parse as a date.
- `Amount` must parse as a decimal.
- `Currency` must be `USD` in the current MVP.
- `Status` is expected to be `Executed`. Other values are logged as warnings.
- `Bank Account Ending Digits` identifies which account received the payout.
  Multiple accounts are allowed but not expected in a single-shop scenario.

### Notes

- This file is the **cash-flow source**. It tells when money actually
  arrived at the bank, which is different from when orders were placed.
- A single deposit usually aggregates **many** payments. The relationship
  is one-to-many: `Deposits (1) → Payments (many)`.
- A reconciliation check should compare the sum of `Payments.Net Amount`
  for a given week of `Funds Available` against the corresponding deposit.
  Differences are expected due to:
  - rolling reserve held by Etsy,
  - chargebacks,
  - payout scheduling delays,
  - cross-week aggregation.
  A difference is a warning, not an error.
- Do **not** use deposits to calculate revenue. Deposits are cash movement,
  not sales.

  
---

## 5. Listings Download

**Source file pattern:** `EtsyListingsDownload*.csv`
**Export location:** Etsy Shop Manager → Listings → Download CSV
**Row meaning:** one listing in the shop's catalog.

### Required columns

| Column | Type | Notes |
|---|---|---|
| `TITLE` | string | Listing title |
| `DESCRIPTION` | string | Full description (may contain newlines) |
| `PRICE` | decimal | Current price |
| `CURRENCY_CODE` | string | ISO code, e.g. `USD` |
| `QUANTITY` | integer | Available quantity |
| `TAGS` | string | Comma-separated tags |

### Optional columns

`MATERIALS`, `IMAGE1`..`IMAGE10`, `VARIATION 1 TYPE`,
`VARIATION 1 NAME`, `VARIATION 1 VALUES`, `VARIATION 2 TYPE`,
`VARIATION 2 NAME`, `VARIATION 2 VALUES`, `VARIATION 3 TYPE`,
`VARIATION 3 NAME`, `VARIATION 3 VALUES`, `SKU`.

### Validation rules

- `TITLE` must be non-empty.
- `PRICE` must parse as a decimal.
- `QUANTITY` must parse as an integer (can be 0).
- `TAGS` is a comma-separated string; individual tags are trimmed.
- `SKU` is often empty; do not rely on it.

### Notes

- **This file does not contain `Listing ID`.** It also has no `created_date`,
  `state`, or `category`. All columns named in the original product
  specification that are not present here cannot be provided by the source.
- Because there is no `Listing ID`, this catalog **cannot be joined** to
  sales data (`EtsySoldOrderItems*.csv` contains `Listing ID`, but the
  catalog does not). This is a hard limitation of the Etsy export.
- Consequence:
  - ABC analysis by catalog is **not possible** in the MVP.
  - "Products with no sales" report is **not possible** in the MVP.
  - Category-level and tag-level analytics are **not possible**.
  - Sales analytics must be built from `EtsySoldOrderItems*.csv` alone.
- A future Phase 2 may allow manual mapping of catalog rows to
  `Listing ID` via SKU or title, but this requires human confirmation
  and confidence scoring and is out of scope for the MVP.