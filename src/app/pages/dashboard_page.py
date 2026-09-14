"""Dashboard page: KPI cards."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.analytics.kpi import KPI, compute_kpi


# (label, kpi attribute, format)
_KPI_CARDS: list[tuple[str, str, str]] = [
    ("Gross Revenue", "gross_revenue", "$"),
    ("Net Revenue", "net_revenue", "$"),
    ("Fees", "fees", "$"),
    ("Refunds", "refunds", "$"),
    ("Orders", "orders_count", "int"),
    ("Items Sold", "items_sold", "int"),
    ("Average Order Value", "average_order_value", "$"),
    ("Average Item Value", "average_item_value", "$"),
    ("Fee Ratio", "fee_ratio", "%"),
    ("Refund Rate", "refund_rate", "%"),
    ("Items per Order", "items_per_order", "float"),
    ("Net after Refunds", "net_after_refunds", "$"),
]


class DashboardPage(QWidget):
    """Grid of KPI cards."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn
        self._value_labels: dict[str, QLabel] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        grid = QGridLayout()
        grid.setSpacing(12)
        outer.addLayout(grid)
        outer.addStretch(1)

        columns = 4
        for index, (label, key, kind) in enumerate(_KPI_CARDS):
            row, col = divmod(index, columns)
            grid.addWidget(self._build_card(label, key, kind), row, col)

    def _build_card(self, label: str, key: str, kind: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { border: 1px solid #cccccc; border-radius: 6px; "
            "background: #fafafa; }"
        )
        card.setMinimumHeight(90)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel(label)
        title.setStyleSheet("color: #555555; font-size: 12px;")
        title.setWordWrap(True)

        value = QLabel("—")
        value.setStyleSheet("font-size: 22px; font-weight: bold;")
        value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(title)
        layout.addWidget(value)
        layout.addStretch(1)

        self._value_labels[key] = value
        return card

    def refresh(self) -> None:
        kpi: KPI = compute_kpi(self._conn)
        for _, key, kind in _KPI_CARDS:
            value = getattr(kpi, key)
            self._value_labels[key].setText(self._format(value, kind))

    @staticmethod
    def _format(value: float, kind: str) -> str:
        if kind == "$":
            return f"${value:,.2f}"
        if kind == "%":
            return f"{value:.1%}"
        if kind == "int":
            return f"{value}"
        return f"{value:,.2f}"