"""Tests for src/core/paths.py."""

from pathlib import Path

from src.core import paths


def test_app_data_dir_returns_path() -> None:
    result = paths.app_data_dir()
    assert isinstance(result, Path)
    assert result.name == paths.APP_NAME


def test_database_file_is_under_app_data() -> None:
    db = paths.database_file()
    assert db.parent == paths.app_data_dir()
    assert db.name == "data.db"


def test_imports_dir_is_under_app_data() -> None:
    d = paths.imports_dir()
    assert d.parent == paths.app_data_dir()
    assert d.name == "imports"


def test_logs_dir_is_under_app_data() -> None:
    d = paths.logs_dir()
    assert d.parent == paths.app_data_dir()
    assert d.name == "logs"