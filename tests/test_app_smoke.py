"""Smoke tests for the PySide6 application shell."""

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture()
def window(qapp, tmp_path: Path):
    from src.app.main_window import MainWindow

    w = MainWindow(db_path=tmp_path / "test.db")
    yield w
    w.close()


def test_window_title(window) -> None:
    assert window.windowTitle() == "Etsy BI Analyzer"


def test_toolbar_buttons_present(window) -> None:
    assert window.import_button.text() == "Import Folder"
    assert window.report_button.text() == "Generate Report"
    assert window.refresh_button.text() == "Refresh"


def test_all_tabs_present(window) -> None:
    expected = [
        "Dashboard", "Sales", "Products",
        "Countries", "Data Quality", "Insights",
    ]
    actual = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert actual == expected


def test_dashboard_shows_zero_kpi_on_empty_db(window) -> None:
    label = window.dashboard_page._value_labels["orders_count"]
    assert label.text() == "0"
    gross = window.dashboard_page._value_labels["gross_revenue"]
    assert gross.text() == "$0.00"


def test_sales_period_combo_has_three_options(window) -> None:
    assert window.sales_page.period_combo.count() == 3


def test_products_limit_default(window) -> None:
    assert window.products_page.limit_spin.value() == 20


def test_refresh_does_not_crash_on_empty_db(window) -> None:
    window.refresh_button.click()
def test_data_quality_grouping_with_issues(window) -> None:
    """Insert several identical issues and check that grouping works."""
    from src.database.repositories import issues_repo

    for i in range(5):
        issues_repo.add_issue(
            window._conn,
            "order_without_items",
            "INFO",
            f"Order {1000 + i} has no line items.",
            table_name="orders",
        )

    window.data_quality_page.refresh()

    # Five identical issues must collapse into one group.
    assert window.data_quality_page.groups_table.rowCount() == 1
    count_item = window.data_quality_page.groups_table.item(0, 3)
    assert count_item.text() == "5"

    # Selecting the group populates details.
    assert window.data_quality_page.details_table.rowCount() == 5


def test_data_quality_severity_summary(window) -> None:
    from src.database.repositories import issues_repo

    issues_repo.add_issue(
        window._conn, "test_check", "ERROR", "boom"
    )
    issues_repo.add_issue(
        window._conn, "test_check", "WARNING", "careful"
    )

    window.data_quality_page.refresh()

    text = window.data_quality_page.summary_label.text()
    assert "ERROR: 1" in text
    assert "WARNING: 1" in text    
    # If we get here without an exception, the refresh path is stable.