# ADR-003: No foreign key constraints on Etsy-derived tables

**Date:** 2026-09-11
**Status:** Accepted

## Context

The schema declares foreign keys from `order_items.order_id` and
`payments.order_id` to `orders.order_id`. During development this
caused tests to fail whenever an `order_items` or `payments` CSV was
loaded before the corresponding `orders` CSV, or whenever the source
files contained orphan references.

Real Etsy exports can contain:

- `SoldOrderItems` rows whose `order_id` is not present in `SoldOrders`
  (e.g. partial exports, different date ranges);
- `Payments` rows for orders outside the current CSV set;
- Rows that arrive in any order the user chooses to import.

## Decision

Remove foreign key constraints from `order_items` and `payments` to
`orders`. Keep plain indexes on the join columns for query performance.

Orphan detection is moved to the reconciliation layer, where it is
recorded as a data quality issue rather than blocking the import.

## Consequences

**Positive:**

- Files can be imported in any order.
- Partial exports do not fail the import.
- Data problems are visible in the Data Quality report instead of
  crashing the pipeline.
- Matches the standard pattern for analytical databases loaded from
  external, uncontrolled sources.

**Negative:**

- The database cannot guarantee referential integrity by itself.
- All joins must be tolerant of missing parents (use LEFT JOIN).
- Orphan detection must be implemented and tested separately.

## Alternatives considered

**Keep the FK and require import order.** Rejected: adds coupling
between steps the user controls, and real exports break the assumption.

**Disable FK enforcement globally.** Rejected: loses constraint
checking on tables where it is safe (`import_id` to `imports`).

## Notes

`order_items.import_id` and `payments.import_id` still reference
`imports.import_id`. That table is fully under our control, so the FK
is safe to keep.