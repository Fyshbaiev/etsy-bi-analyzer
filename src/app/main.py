"""Application entry point.

Run with:  python -m src.app.main
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Etsy BI Analyzer")
    app.setOrganizationName("EtsyBIAnalyzer")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())