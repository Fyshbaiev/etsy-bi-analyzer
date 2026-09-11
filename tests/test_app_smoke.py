"""Smoke tests for the PySide6 application shell."""

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def qapp():
    """One QApplication shared across the module."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_creates(qapp, tmp_path: Path) -> None:
    from src.app.main_window import MainWindow

    w = MainWindow(db_path=tmp_path / "test.db")
    try:
        assert w.windowTitle() == "Etsy BI Analyzer"
    finally:
        w.close()


def test_main_window_has_toolbar_buttons(qapp, tmp_path: Path) -> None:
    from src.app.main_window import MainWindow

    w = MainWindow(db_path=tmp_path / "test.db")
    try:
        assert w.import_button.text() == "Import Folder"
        assert w.report_button.text() == "Generate Report"
    finally:
        w.close()


def test_main_window_has_two_tabs(qapp, tmp_path: Path) -> None:
    from src.app.main_window import MainWindow

    w = MainWindow(db_path=tmp_path / "test.db")
    try:
        assert w.tabs.count() == 2
        assert w.tabs.tabText(0) == "Dashboard"
        assert w.tabs.tabText(1) == "Data Quality"
    finally:
        w.close()


def test_dashboard_shows_zero_kpi_on_empty_db(qapp, tmp_path: Path) -> None:
    from src.app.main_window import MainWindow

    w = MainWindow(db_path=tmp_path / "test.db")
    try:
        # orders_count is stored as a plain integer
        assert w._kpi_labels["orders_count"].text() == "0"
        # gross revenue is formatted as $0.00
        assert w._kpi_labels["gross_revenue"].text() == "$0.00"
    finally:
        w.close()