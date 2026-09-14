"""Products page: top listings by revenue."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.analytics.kpi import top_listings_by_revenue


class ProductsPage(QWidget):
    """Top listings by total item revenue."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        header.addWidget(QLabel("Top:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(5, 500)
        self.limit_spin.setValue(20)
        self.limit_spin.setSingleStep(5)
        self.limit_spin.valueChanged.connect(self.refresh)
        header.addWidget(self.limit_spin)
        header.addStretch(1)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Listing ID", "Item Name", "Revenue", "Units", "Orders"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.Stretch)
        head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        limit = self.limit_spin.value()
        rows = top_listings_by_revenue(self._conn, limit=limit)

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["listing_id"])))
            self.table.setItem(
                i, 1, QTableWidgetItem(str(row["item_name"] or ""))
            )
            revenue_item = QTableWidgetItem(f"${row['revenue']:,.2f}")
            revenue_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 2, revenue_item)

            units_item = QTableWidgetItem(str(row["units"]))
            units_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, units_item)

            orders_item = QTableWidgetItem(str(row["orders"]))
            orders_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 4, orders_item)