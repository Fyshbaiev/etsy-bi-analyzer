# Metrics

This document defines every business metric calculated by the application.
Each metric has exactly one definition, one formula, and one source file.
Any change to a formula must be reflected here first.

All amounts are in USD. Multi-currency is out of scope for the MVP.

## Naming and terminology

The Etsy exports use several similar-looking amounts. They are **not**
interchangeable. The following table fixes the meaning used everywhere
in this project.

| Source column | Meaning | Used for revenue? |
|---|---|---|
| `SoldOrders.Order Value` | Gross order amount before discount | No |
| `SoldOrders.Discount Amount` | Total discount applied to the order | No |
| `SoldOrders.Order Total` | Amount the buyer saw at checkout (may include tax presentation) | No |
| `SoldOrders.Card Processing Fees` | Payment processing fees | No |
| `SoldOrders.Order Net` | Amount credited to the shop | No |
| `Payments.Gross Amount` | Amount charged to the buyer after discount | **Yes** |
| `Payments.Fees` | Total fees kept by Etsy | No |
| `Payments.Net Amount` | Amount credited to the shop | **Yes** |
| `Payments.Refund Amount` | Amount refunded to the buyer | No |
| `Deposits.Amount` | Cash transferred to the bank | No |

**Rule of thumb:** revenue comes from the `Payments` file, never from
`SoldOrders`. `SoldOrders` is used for validation and cross-checks only.

## Core metrics

### Gross Revenue
Total amount charged to buyers, after discounts, before fees and refunds.
Gross Revenue = SUM(Payments.Gross Amount)

Source: `EtsyDirectCheckoutPayments*.csv`

### Fees
Total fees kept by Etsy (transaction fee + payment processing).
Fees = SUM(Payments.Fees)

Source: `EtsyDirectCheckoutPayments*.csv`

Note: fees are recorded at the order level. Per-product fee attribution
is not possible from the current exports.

### Refunds
Total amount refunded to buyers.
Refunds = SUM(Payments.Refund Amount)

Source: `EtsyDirectCheckoutPayments*.csv`

### Net Revenue
Amount credited to the shop after fees, before refunds.
Net Revenue = SUM(Payments.Net Amount)

Source: `EtsyDirectCheckoutPayments*.csv`

### Net after Refunds
Amount the shop actually keeps after refunds.
Net after Refunds = Net Revenue − Refunds

Source: `EtsyDirectCheckoutPayments*.csv`

### Fee Ratio
Share of gross revenue consumed by fees.
Fee Ratio = Fees / Gross Revenue

Expressed as a percentage. Typical range: 8–15%. Values above 15% are
flagged as a warning in the Insights page.

### Refund Rate
Share of gross revenue returned to buyers as refunds.
Refund Rate = Refunds / Gross Revenue

Expressed as a percentage. Typical range: 0–3%. Values above 3% are
flagged as a warning.

## Order metrics

### Orders
Number of distinct orders that resulted in a payment.
Orders = COUNT(DISTINCT Payments.Order ID)

Source: `EtsyDirectCheckoutPayments*.csv`

### Items Sold
Total number of physical or digital items sold, including quantities > 1.
Items Sold = SUM(OrderItems.Quantity)

Source: `EtsySoldOrderItems*.csv`

### Average Order Value (AOV)
Average amount charged per order, before fees and refunds.
AOV = Gross Revenue / Orders

Source: `EtsyDirectCheckoutPayments*.csv`

### Average Item Value (AIV)
Average amount charged per individual item sold.
AIV = Gross Revenue / Items Sold

Source: `Payments` and `OrderItems`

### Items per Order
Average number of items per order.
Items per Order = Items Sold / Orders

## Product metrics

All product metrics are computed **per `Listing ID`** using
`EtsySoldOrderItems*.csv`. The catalog file is not used because it has no
`Listing ID` (see `docs/data-contracts.md`).

### Product Revenue
Sum of item totals for a given `Listing ID`.
Product Revenue = SUM(OrderItems.Item Total) WHERE Listing ID = ?

### Product Orders
Number of distinct orders containing this listing.
Product Orders = COUNT(DISTINCT OrderItems.Order ID) WHERE Listing ID = ?

### Product Units
Total quantity sold for this listing.
Product Units = SUM(OrderItems.Quantity) WHERE Listing ID = ?

### Product Average Price
Average unit price.
Product Average Price = SUM(OrderItems.Item Total) / SUM(OrderItems.Quantity)

## ABC analysis

ABC analysis ranks products by revenue and groups them into three classes:

- **A** — products that generate the first ~80% of cumulative revenue
- **B** — the next ~15%
- **C** — the remaining ~5%

Formula:

1. Sort all `Listing ID` by `Product Revenue` descending.
2. Compute cumulative revenue and cumulative share.
3. Assign class based on cumulative share thresholds: 80% / 95% / 100%.

Source: `EtsySoldOrderItems*.csv`

Note: ABC is computed over **sold listings only**. Listings with zero
sales cannot be included because the catalog has no `Listing ID`.

## Time series

### Revenue by period
Aggregate `Gross Revenue` by day, week, or month.
Revenue(period) = SUM(Payments.Gross Amount) GROUP BY period(Payments.Order Date)

### Growth rates
- MoM (month over month): `(Revenue(m) − Revenue(m−1)) / Revenue(m−1)`
- YoY (year over year): requires two full years of data, otherwise not calculated.

Both are expressed as percentages. When the previous period has zero
revenue, growth is reported as `N/A`, never as a division by zero.

## Geographic metrics

### Revenue by Country

`Payments` has no country column, so join through `SoldOrders`:
Revenue by Country = SUM(Payments.Gross Amount)
JOIN SoldOrders ON Payments.Order ID = SoldOrders.Order ID
GROUP BY SoldOrders.Ship Country

Source: `EtsyDirectCheckoutPayments*.csv` joined with `EtsySoldOrders*.csv`.

### Orders by Country
Orders by Country = COUNT(DISTINCT Payments.Order ID)
JOIN SoldOrders ON Payments.Order ID = SoldOrders.Order ID
GROUP BY SoldOrders.Ship Country

## Cash flow metrics

### Deposits Total
Deposits Total = SUM(Deposits.Amount)

Source: `EtsyDeposits*.csv`

### Deposit Count
Deposit Count = COUNT(Deposits)

### Average Deposit Size
Average Deposit Size = Deposits Total / Deposit Count

### Deposit Reconciliation
For each week defined by `Payments.Funds Available`:
Expected Deposit(week) = SUM(Payments.Net Amount) WHERE Funds Available IN week
Actual Deposit(week) = SUM(Deposits.Amount) WHERE Date IN week
Difference(week) = Expected Deposit − Actual Deposit

A difference is logged as a warning, not an error. Expected causes:
rolling reserve, chargebacks, cross-week aggregation, timing offsets.

## Data quality metrics

### Valid Row Ratio
Valid Row Ratio = Valid Rows / Total Rows

Computed per import. Values below 95% trigger a warning on the
Data Quality page.

### Duplicate Rate
Duplicate Rate = Duplicate Rows / Total Rows

## Metrics NOT computed in the MVP

The following metrics are intentionally excluded. They cannot be
calculated from the available exports, or they require data the shop
owner has not provided.

| Metric | Reason |
|---|---|
| Profit | COGS, ads, packaging, and other expenses are unknown |
| Etsy fees split (transaction / processing / listing) | Fees arrive as one number |
| Per-product fees | Fees are recorded at the order level |
| Products with no sales | Catalog has no `Listing ID` |
| Category-level analytics | Catalog has no category |
| Tag-level analytics | Catalog has tags, sales have no tags — no join |
| Repeat buyer rate | Buyer identity is not stable across all exports |
| Seasonality | Requires more than one year of data |
| YoY growth | Same reason |

## Rounding rules

- All monetary values are stored with full precision in SQLite.
- Display rounds to 2 decimals for amounts, 1 decimal for percentages.
- Excel export uses the same rounding.
- Never round intermediate values; round only at the moment of display.

## Currency

All exports used in the MVP are in USD. If a future export contains a
different currency, the row must be rejected at import and logged as a
data quality issue. Currency conversion is out of scope.