"""Filesystem paths used by the application.

All runtime data lives outside the project folder, in the user's
%APPDATA% directory on Windows. This keeps the Git repository clean
and works when the app is packaged as a .exe.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "EtsyBIAnalyzer"


def app_data_dir() -> Path:
    """Return the application data directory.

    On Windows this is %APPDATA%\\EtsyBIAnalyzer.
    On other systems (for development and CI) it falls back to
    ~/.local/share/EtsyBIAnalyzer.
    """
    base = os.environ.get("APPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / ".local" / "share"
    return root / APP_NAME


def config_file() -> Path:
    """Path to the user configuration file."""
    return app_data_dir() / "config.json"


def database_file() -> Path:
    """Path to the SQLite database."""
    return app_data_dir() / "data.db"


def imports_dir() -> Path:
    """Directory where copies of imported CSV files are stored."""
    return app_data_dir() / "imports"


def logs_dir() -> Path:
    """Directory where log files are stored."""
    return app_data_dir() / "logs"


def ensure_app_dirs() -> None:
    """Create all application directories if they do not exist."""
    for path in (app_data_dir(), imports_dir(), logs_dir()):
        path.mkdir(parents=True, exist_ok=True)