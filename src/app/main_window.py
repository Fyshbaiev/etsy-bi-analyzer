"""Main application window.

This is the minimum viable UI:
  - two toolbar buttons: Import Folder, Generate Report
  - two tabs: Dashboard (KPI cards), Data Quality (issue table)
  - a status bar

All data comes from the analytics, reconciliation, and reports modules.
No business logic lives here.
"""

from __future__ import annotations

import sqlite3
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.analytics.kpi import KPI, compute_kpi
from src.core import paths
from src.database.connection import connect_and_init
from src.database.repositories import issues_repo
from src.importer import service
from src.reports import excel


# KPI labels shown in the Dashboard in the order they appear.
_KPI_FIELDS: list[tuple[str, str, str]] = [
    ("Gross Revenue", "gross_revenue", "$"),
    ("Net Revenue", "net_revenue", "$"),
    ("Fees", "fees", "$"),
    ("Refunds", "refunds", "$"),
    ("Orders", "orders_count", ""),
    ("Items Sold", "items_sold", ""),
    ("Average Order Value", "average_order_value", "$"),
    ("Fee Ratio", "fee_ratio", "%"),
]


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Etsy BI Analyzer")
        self.resize(1000, 700)

        self._db_path = db_path or paths.database_file()
        paths.ensure_app_dirs()
        self._conn: sqlite3.Connection = connect_and_init(self._db_path)

        self._kpi_labels: dict[str, QLabel] = {}

        self._build_toolbar()
        self._build_tabs()
        self._build_status_bar()

        self._refresh_all()

    # -----------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = self.addToolBar("Actions")
        bar.setMovable(False)

        self.import_button = QPushButton("Import Folder")
        self.import_button.clicked.connect(self._on_import_folder)

        self.report_button = QPushButton("Generate Report")
        self.report_button.clicked.connect(self._on_generate_report)

        bar.addWidget(self.import_button)
        bar.addWidget(self.report_button)

    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._build_data_quality_tab(), "Data Quality")
        self.setCentralWidget(self.tabs)

    def _build_dashboard_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        box = QGroupBox("Key Performance Indicators")
        form = QVBoxLayout(box)

        for label, key, _ in _KPI_FIELDS:
            row = QHBoxLayout()
            title = QLabel(label)
            title.setMinimumWidth(180)
            value = QLabel("—")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value.setStyleSheet("font-weight: bold; font-size: 14px;")
            row.addWidget(title)
            row.addWidget(value)
            form.addLayout(row)
            self._kpi_labels[key] = value

        layout.addWidget(box)
        layout.addStretch(1)
        return widget

    def _build_data_quality_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(4)
        self.issues_table.setHorizontalHeaderLabels(
            ["Severity", "Check", "Table", "Message"]
        )
        header = self.issues_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        layout.addWidget(self.issues_table)
        return widget

    def _build_status_bar(self) -> None:
        self.statusBar().showMessage("Ready")

    # -----------------------------------------------------------
    # Actions
    # -----------------------------------------------------------

    def _on_import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder with Etsy CSV files"
        )
        if not folder:
            return

        folder_path = Path(folder)
        csv_files = sorted(folder_path.glob("*.csv"))
        if not csv_files:
            QMessageBox.information(
                self, "Import", "No CSV files found in the selected folder."
            )
            return

        imported = 0
        skipped = 0
        failed = 0
        details: list[str] = []

        for csv_file in csv_files:
            try:
                result = service.import_file(self._conn, csv_file)
                if result.already_imported:
                    skipped += 1
                    details.append(f"SKIP  {csv_file.name} (already imported)")
                elif result.status == "FAILED":
                    failed += 1
                    details.append(f"FAIL  {csv_file.name}")
                else:
                    imported += 1
                    details.append(
                        f"OK    {csv_file.name}  "
                        f"({result.rows_inserted}/{result.rows_total} rows)"
                    )
            except ValueError:
                skipped += 1
                details.append(f"SKIP  {csv_file.name} (unsupported type)")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                details.append(f"FAIL  {csv_file.name}: {exc}")

        summary = (
            f"Imported: {imported}\n"
            f"Skipped:  {skipped}\n"
            f"Failed:   {failed}"
        )
        QMessageBox.information(
            self,
            "Import complete",
            summary + "\n\n" + "\n".join(details),
        )

        self._refresh_all()

    def _on_generate_report(self) -> None:
        default_name = str(Path.home() / "etsy_business_report.xlsx")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel report",
            default_name,
            "Excel files (*.xlsx)",
        )
        if not file_path:
            return

        try:
            excel.build_report(self._conn, file_path, run_reconciliation=True)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Report generation failed",
                f"{exc}\n\n{traceback.format_exc()}",
            )
            return

        QMessageBox.information(
            self, "Report", f"Report saved to:\n{file_path}"
        )
        self._refresh_all()

    # -----------------------------------------------------------
    # Refresh
    # -----------------------------------------------------------

    def _refresh_all(self) -> None:
        self._refresh_kpi()
        self._refresh_issues()
        self.statusBar().showMessage(
            f"Database: {self._db_path}"
        )

    def _refresh_kpi(self) -> None:
        kpi: KPI = compute_kpi(self._conn)
        for _, key, kind in _KPI_FIELDS:
            value = getattr(kpi, key)
            if kind == "$":
                text = f"${value:,.2f}"
            elif kind == "%":
                text = f"{value:.1%}"
            else:
                text = f"{value}"
            self._kpi_labels[key].setText(text)

    def _refresh_issues(self) -> None:
        issues = issues_repo.list_issues(self._conn, limit=200)
        self.issues_table.setRowCount(len(issues))
        for row_idx, issue in enumerate(issues):
            self.issues_table.setItem(
                row_idx, 0, QTableWidgetItem(issue["severity"])
            )
            self.issues_table.setItem(
                row_idx, 1, QTableWidgetItem(issue["check_name"])
            )
            self.issues_table.setItem(
                row_idx, 2, QTableWidgetItem(issue["table_name"] or "")
            )
            self.issues_table.setItem(
                row_idx, 3, QTableWidgetItem(issue["message"])
            )

    # -----------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._conn is not None:
            self._conn.close()
        super().closeEvent(event)