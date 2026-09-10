# Reconciliation

This document describes how the application cross-checks data from
different Etsy exports against each other. Reconciliation catches
inconsistencies that no single file reveals.

Every check produces one of three outcomes:

- **OK** — the values match within tolerance.
- **Warning** — the difference is explainable and expected.
- **Error** — the difference indicates a data problem.

All findings are stored in the `data_quality_issues` table and shown
on the Data Quality page.

## Check 1: Orders ↔ Payments

**Purpose:** verify that every order in `SoldOrders` has a matching
payment record, and that the amounts agree.

**Join key:** `Order ID`

**Checks:**

1. Every `SoldOrders.Order ID` must exist in `Payments.Order ID`.
   - Missing payment → **Error**.
2. Every `Payments.Order ID` must exist in `SoldOrders.Order ID`.
   - Orphan payment → **Error**.
3. `Payments.Gross Amount` should equal
   `SoldOrders.Order Value − SoldOrders.Discount Amount`.
   - Mismatch > 0.01 USD → **Warning**.
4. `Payments.Fees` should equal `SoldOrders.Card Processing Fees`.
   - Mismatch > 0.01 USD → **Warning**.
5. `Payments.Net Amount` should equal `SoldOrders.Order Net`.
   - Mismatch > 0.01 USD → **Warning**.

**Notes:**

- Checks 3–5 are warnings, not errors, because the Etsy exports
  occasionally present slightly different rounded values in the two
  files.
- Tolerance: **0.01 USD**. Anything above is worth logging.

## Check 2: Orders ↔ Order Items

**Purpose:** verify that the order-level totals are consistent with
the sum of line items.

**Join key:** `Order ID`

**Checks:**

1. Every `SoldOrderItems.Order ID` must exist in `SoldOrders.Order ID`.
   - Missing order → **Error**.
2. For each `Order ID`, `SUM(OrderItems.Item Total)` should equal
   `SoldOrders.Order Value`.
   - Mismatch > 0.01 USD → **Warning**.
3. For each `Order ID`, `COUNT(OrderItems)` should equal
   `SoldOrders.Number of Items`.
   - Mismatch → **Warning**.
4. For each row, `OrderItems.Item Total` should equal
   `OrderItems.Price × OrderItems.Quantity`.
   - Mismatch > 0.01 USD → **Warning**.

**Notes:**

- `Discount Amount` in `SoldOrderItems` is a per-line discount.
  It is separate from the order-level discount and should not be
  subtracted again when computing line totals.

## Check 3: Payments ↔ Deposits

**Purpose:** verify that the cash that should have been paid out
matches the deposits that actually arrived at the bank.

**Join key:** week of `Payments.Funds Available`

**Checks:**

1. For each ISO week, compute:
Expected(week) = SUM(Payments.Net Amount) WHERE Funds Available IN week
Actual(week) = SUM(Deposits.Amount) WHERE Date IN week
2. Compute `Difference(week) = Expected − Actual`.

**Outcome classification:**

- Difference within ±5% of expected → **OK**.
- Difference between 5% and 15% → **Warning**.
- Difference above 15% → **Error** (worth investigating manually).

**Known causes of differences (do not treat as errors):**

- Etsy holds a rolling reserve for new shops.
- Chargebacks are deducted from payouts.
- Deposits can aggregate payments across week boundaries.
- Bank processing delays shift the actual deposit by 1–3 days.

**Notes:**

- Never use deposits to compute revenue. Deposits are cash movement,
not sales.
- Reconciliation is a check, not a source of truth. The `Payments`
file remains the authoritative source for revenue.

## Check 4: Refunds

**Purpose:** verify that refunds are consistent with order-level data.

**Source:** `Payments.Refund Amount`

**Checks:**

1. For every `Payment ID` with `Refund Amount > 0`:
- Record the refund as a data quality event with severity **Info**.
- Verify that the refunded order exists in `SoldOrders`.
  - Missing order → **Error**.
2. Compare `SUM(Refund Amount)` against `SUM(Order Total)` for the same
period and log the refund ratio.

**Notes:**

- Etsy does not export a refund reason. The application records only
the fact and the amount.
- A single order may have multiple refund events with different
timestamps. Each is recorded separately.

## Check 5: Currency consistency

**Purpose:** verify that all imports use the same currency.

**Checks:**

1. Every value in `Currency` across `SoldOrders`, `OrderItems`,
`Payments`, and `Deposits` must be `USD`.
2. Any other value → **Error**, and the row is rejected at import.

**Notes:**

- Multi-currency support is out of scope for the MVP.
- If a future export contains a non-USD row, the whole import is
paused and the user is notified.

## Check 6: Import integrity

**Purpose:** prevent duplicate imports of the same file.

**Checks:**

1. Compute the SHA-256 hash of every imported file.
2. Compare against `imports.file_hash`.
3. Duplicate hash → skip the file and record a data quality event.

**Notes:**

- The user can force a re-import by deleting the previous import
record from the Settings page (Phase 2).

## Severity levels

| Level | Meaning | Visible to user? |
|---|---|---|
| Info | Expected event, worth recording | Yes, collapsed by default |
| Warning | Discrepancy that needs attention but does not block analytics | Yes, always visible |
| Error | Data cannot be trusted | Yes, blocks affected reports |

## What reconciliation does NOT do

- It does not fix data. Fixing is the user's decision.
- It does not delete rows. Every issue is recorded and left in place.
- It does not guess missing values. Missing data stays missing.
- It does not reconcile refunds against the original line items,
because Etsy does not provide that link.