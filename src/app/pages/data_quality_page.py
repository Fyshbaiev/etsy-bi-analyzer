"""Data Quality page: grouped summary and detailed view.

The page has two stacked tables:
  - top: one row per (check_name, severity) with a count
  - bottom: individual issues, filtered by the top selection

This avoids showing hundreds of identical rows.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database.repositories import issues_repo


_SEVERITY_COLORS = {
    "ERROR": QColor("#f8d7da"),
    "WARNING": QColor("#fff3cd"),
    "INFO": QColor("#d1ecf1"),
}


class DataQualityPage(QWidget):
    """Grouped data quality view."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.summary_label = QLabel("No issues.")
        self.summary_label.setStyleSheet("font-size: 13px; padding: 4px;")
        layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Vertical)

        # Top: grouped
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(4)
        self.groups_table.setHorizontalHeaderLabels(
            ["Severity", "Check", "Table", "Count"]
        )
        self.groups_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.groups_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.groups_table.setSelectionMode(QTableWidget.SingleSelection)
        head = self.groups_table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.Stretch)
        head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.groups_table.itemSelectionChanged.connect(
            self._on_group_selected
        )

        # Bottom: individual issues
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(4)
        self.details_table.setHorizontalHeaderLabels(
            ["Severity", "Row Ref", "Field", "Message"]
        )
        self.details_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.details_table.setSelectionBehavior(QTableWidget.SelectRows)
        head2 = self.details_table.horizontalHeader()
        head2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        head2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        head2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        head2.setSectionResizeMode(3, QHeaderView.Stretch)

        splitter.addWidget(self.groups_table)
        splitter.addWidget(self.details_table)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self._groups: list[dict] = []

    # -----------------------------------------------------------

    def refresh(self) -> None:
        counts = issues_repo.count_by_severity(self._conn)
        errors = counts.get("ERROR", 0)
        warnings = counts.get("WARNING", 0)
        infos = counts.get("INFO", 0)
        total = errors + warnings + infos

        self.summary_label.setText(
            f"Total: {total}   |   "
            f"ERROR: {errors}   WARNING: {warnings}   INFO: {infos}"
        )

        self._groups = issues_repo.grouped_counts(self._conn)
        self.groups_table.setRowCount(len(self._groups))

        for i, group in enumerate(self._groups):
            severity = group["severity"]
            severity_item = QTableWidgetItem(severity)
            color = _SEVERITY_COLORS.get(severity)
            if color is not None:
                severity_item.setBackground(color)
            self.groups_table.setItem(i, 0, severity_item)
            self.groups_table.setItem(
                i, 1, QTableWidgetItem(group["check_name"])
            )
            self.groups_table.setItem(
                i, 2, QTableWidgetItem(group["table_name"] or "")
            )
            count_item = QTableWidgetItem(str(group["count"]))
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.groups_table.setItem(i, 3, count_item)

        self.details_table.setRowCount(0)

        if self._groups:
            self.groups_table.selectRow(0)

    # -----------------------------------------------------------

    def _on_group_selected(self) -> None:
        rows = self.groups_table.selectionModel().selectedRows()
        if not rows:
            self.details_table.setRowCount(0)
            return
        index = rows[0].row()
        if index < 0 or index >= len(self._groups):
            return

        check_name = self._groups[index]["check_name"]
        details = issues_repo.issues_for_check(self._conn, check_name)

        self.details_table.setRowCount(len(details))
        for i, issue in enumerate(details):
            severity_item = QTableWidgetItem(issue["severity"])
            color = _SEVERITY_COLORS.get(issue["severity"])
            if color is not None:
                severity_item.setBackground(color)
            self.details_table.setItem(i, 0, severity_item)
            self.details_table.setItem(
                i, 1, QTableWidgetItem(issue["row_ref"] or "")
            )
            self.details_table.setItem(
                i, 2, QTableWidgetItem(issue["field_name"] or "")
            )
            self.details_table.setItem(
                i, 3, QTableWidgetItem(issue["message"])
            )