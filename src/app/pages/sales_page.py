"""Sales page: revenue over time."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.analytics.kpi import revenue_by_period


class SalesPage(QWidget):
    """Revenue aggregated by day, week, or month."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        header.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Month", "Week", "Day"])
        self.period_combo.currentTextChanged.connect(self.refresh)
        header.addWidget(self.period_combo)
        header.addStretch(1)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Period", "Revenue", "Orders"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.Stretch)
        head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        period = self.period_combo.currentText().lower()
        rows = revenue_by_period(self._conn, period=period)

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            period_item = QTableWidgetItem(str(row["period"]))
            revenue_item = QTableWidgetItem(f"${row['revenue']:,.2f}")
            revenue_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            orders_item = QTableWidgetItem(str(row["orders"]))
            orders_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.table.setItem(i, 0, period_item)
            self.table.setItem(i, 1, revenue_item)
            self.table.setItem(i, 2, orders_item)