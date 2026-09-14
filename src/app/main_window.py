"""Main application window.

Assembles the toolbar, tabs, and per-page widgets. All data flows
from analytics, insights, and reports modules — no business logic
lives here.
"""

from __future__ import annotations

import sqlite3
import traceback
from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
)

from src.app.pages.countries_page import CountriesPage
from src.app.pages.dashboard_page import DashboardPage
from src.app.pages.data_quality_page import DataQualityPage
from src.app.pages.insights_page import InsightsPage
from src.app.pages.products_page import ProductsPage
from src.app.pages.sales_page import SalesPage
from src.core import paths
from src.database.connection import connect_and_init
from src.importer import service
from src.reports import excel


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Etsy BI Analyzer")
        self.resize(1200, 800)

        self._db_path = db_path or paths.database_file()
        paths.ensure_app_dirs()
        self._conn: sqlite3.Connection = connect_and_init(self._db_path)

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

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_all)

        bar.addWidget(self.import_button)
        bar.addWidget(self.report_button)
        bar.addSeparator()
        bar.addWidget(self.refresh_button)

    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()

        self.dashboard_page = DashboardPage(self._conn)
        self.sales_page = SalesPage(self._conn)
        self.products_page = ProductsPage(self._conn)
        self.countries_page = CountriesPage(self._conn)
        self.data_quality_page = DataQualityPage(self._conn)
        self.insights_page = InsightsPage(self._conn)

        self.tabs.addTab(self.dashboard_page, "Dashboard")
        self.tabs.addTab(self.sales_page, "Sales")
        self.tabs.addTab(self.products_page, "Products")
        self.tabs.addTab(self.countries_page, "Countries")
        self.tabs.addTab(self.data_quality_page, "Data Quality")
        self.tabs.addTab(self.insights_page, "Insights")

        self.setCentralWidget(self.tabs)

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
        for page in (
            self.dashboard_page,
            self.sales_page,
            self.products_page,
            self.countries_page,
            self.data_quality_page,
            self.insights_page,
        ):
            page.refresh()
        self.statusBar().showMessage(f"Database: {self._db_path}")

    # -----------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._conn is not None:
            self._conn.close()
        super().closeEvent(event)