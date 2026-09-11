"""Shared pytest configuration.

The Qt offscreen platform must be selected before PySide6 is imported,
otherwise tests that create a QApplication will try to open a real window.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")