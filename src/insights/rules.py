"""Rule-based business insights.

Each rule inspects KPI values and issues findings. Rules are pure
functions: they take data in, return a list of findings. No database
access here — the caller loads data and passes it in.

Findings are later rendered in the UI and Excel report. The LLM
module (Phase 2) will rephrase these findings, not compute them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum

from src.analytics.kpi import KPI, compute_kpi, top_listings_by_revenue
from src.database.repositories import issues_repo


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    RISK = "RISK"


@dataclass
class Insight:
    """One human-readable finding about the shop."""

    code: str
    severity: Severity
    title: str
    detail: str


# ---------------------------------------------------------------
# Thresholds. Kept as module constants so tests can reference them
# and future config can override them.
# ---------------------------------------------------------------

FEE_RATIO_WARNING = 0.12      # fees above 12% of gross
REFUND_RATE_WARNING = 0.03    # refunds above 3% of gross
TOP_N_FOR_CONCENTRATION = 5   # how many listings to check for Pareto
CONCENTRATION_WARNING = 0.60  # top N share above this is a risk
NO_SALES_INFO = 1             # at least this many orders needed


# ---------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------

def rule_no_data(kpi: KPI) -> list[Insight]:
    if kpi.orders_count == 0:
        return [Insight(
            code="no_data",
            severity=Severity.WARNING,
            title="No orders found",
            detail="Import Etsy CSVs to see analytics.",
        )]
    return []


def rule_fee_ratio(kpi: KPI) -> list[Insight]:
    if kpi.gross_revenue <= 0:
        return []
    if kpi.fee_ratio > FEE_RATIO_WARNING:
        return [Insight(
            code="high_fee_ratio",
            severity=Severity.WARNING,
            title=f"Etsy fees are {kpi.fee_ratio:.1%} of gross revenue",
            detail=(
                f"Fees of ${kpi.fees:,.2f} on gross revenue of "
                f"${kpi.gross_revenue:,.2f}. Typical range is 8–12%."
            ),
        )]
    return [Insight(
        code="normal_fee_ratio",
        severity=Severity.INFO,
        title=f"Etsy fees are {kpi.fee_ratio:.1%} of gross revenue",
        detail=f"Fees: ${kpi.fees:,.2f} on ${kpi.gross_revenue:,.2f}.",
    )]


def rule_refund_rate(kpi: KPI) -> list[Insight]:
    if kpi.gross_revenue <= 0:
        return []
    if kpi.refunds <= 0:
        return [Insight(
            code="no_refunds",
            severity=Severity.INFO,
            title="No refunds recorded",
            detail="No refunds in the imported dataset.",
        )]
    if kpi.refund_rate > REFUND_RATE_WARNING:
        return [Insight(
            code="high_refund_rate",
            severity=Severity.RISK,
            title=f"Refund rate is {kpi.refund_rate:.1%}",
            detail=(
                f"Refunds of ${kpi.refunds:,.2f} on gross revenue of "
                f"${kpi.gross_revenue:,.2f}. Typical range is 0–3%."
            ),
        )]
    return [Insight(
        code="normal_refund_rate",
        severity=Severity.INFO,
        title=f"Refund rate is {kpi.refund_rate:.1%}",
        detail=f"Refunds: ${kpi.refunds:,.2f}.",
    )]


def rule_average_order_value(kpi: KPI) -> list[Insight]:
    if kpi.orders_count == 0:
        return []
    return [Insight(
        code="average_order_value",
        severity=Severity.INFO,
        title=f"Average order value is ${kpi.average_order_value:,.2f}",
        detail=(
            f"Across {kpi.orders_count} orders and "
            f"{kpi.items_sold} items sold "
            f"({kpi.items_per_order:.2f} items per order)."
        ),
    )]


def rule_top_listings_concentration(
    conn: sqlite3.Connection, top_n: int = TOP_N_FOR_CONCENTRATION
) -> list[Insight]:
    """Detect Pareto concentration: top N listings share of revenue."""
    top = top_listings_by_revenue(conn, limit=top_n)
    if not top:
        return []
    total_row = conn.execute(
        "SELECT COALESCE(SUM(item_total), 0) AS total FROM order_items"
    ).fetchone()
    total = float(total_row["total"])
    if total <= 0:
        return []

    top_revenue = sum(r["revenue"] for r in top)
    share = top_revenue / total
    if share >= CONCENTRATION_WARNING:
        return [Insight(
            code="revenue_concentration",
            severity=Severity.WARNING,
            title=(
                f"Top {len(top)} listings generate {share:.1%} of item revenue"
            ),
            detail=(
                f"${top_revenue:,.2f} out of ${total:,.2f}. "
                f"Revenue is highly concentrated."
            ),
        )]
    return [Insight(
        code="revenue_distribution",
        severity=Severity.INFO,
        title=f"Top {len(top)} listings generate {share:.1%} of item revenue",
        detail=f"${top_revenue:,.2f} out of ${total:,.2f}.",
    )]


def rule_best_performer(conn: sqlite3.Connection) -> list[Insight]:
    top = top_listings_by_revenue(conn, limit=1)
    if not top:
        return []
    best = top[0]
    name = best["item_name"] or best["listing_id"]
    return [Insight(
        code="best_performer",
        severity=Severity.INFO,
        title=f"Top listing: {name}",
        detail=(
            f"${best['revenue']:,.2f} revenue across "
            f"{best['orders']} orders and {best['units']} units."
        ),
    )]


def rule_data_quality(
    conn: sqlite3.Connection,
    error_threshold: int = 1,
) -> list[Insight]:
    """Report on unresolved data quality issues."""
    counts = issues_repo.count_by_severity(conn)
    errors = counts.get("ERROR", 0)
    warnings = counts.get("WARNING", 0)

    findings: list[Insight] = []
    if errors >= error_threshold:
        findings.append(Insight(
            code="data_quality_errors",
            severity=Severity.RISK,
            title=f"{errors} data quality errors",
            detail="Open the Data Quality page for details.",
        ))
    if warnings > 0:
        findings.append(Insight(
            code="data_quality_warnings",
            severity=Severity.WARNING,
            title=f"{warnings} data quality warnings",
            detail="Some numbers may be off. Review the Data Quality page.",
        ))
    if not findings:
        findings.append(Insight(
            code="data_quality_clean",
            severity=Severity.INFO,
            title="No data quality issues",
            detail="All reconciliation checks passed.",
        ))
    return findings


# ---------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------

def generate_insights(conn: sqlite3.Connection) -> list[Insight]:
    """Run all rules and return the combined list of findings."""
    kpi = compute_kpi(conn)

    findings: list[Insight] = []
    findings.extend(rule_no_data(kpi))
    if kpi.orders_count == 0:
        return findings

    findings.extend(rule_fee_ratio(kpi))
    findings.extend(rule_refund_rate(kpi))
    findings.extend(rule_average_order_value(kpi))
    findings.extend(rule_best_performer(conn))
    findings.extend(rule_top_listings_concentration(conn))
    findings.extend(rule_data_quality(conn))
    return findings