"""Tests for broken_clock_storage backend selection."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _reload_storage():
    """Remove cached module so next import picks up fresh env vars."""
    if "app.broken_clock.storage" in sys.modules:
        del sys.modules["app.broken_clock.storage"]
    if "app.broken_clock.storage_sqlite" in sys.modules:
        del sys.modules["app.broken_clock.storage_sqlite"]
    import app.broken_clock.storage as mod  # noqa: F811
    return mod


def test_default_backend_is_sqlite(monkeypatch):
    """Missing STORAGE_BACKEND — get_db_path() works with sqlite."""
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("APP_DB_PATH", "/tmp/test_default.db")
    mod = _reload_storage()
    # Calling a storage function should succeed
    assert mod.get_db_path() == "/tmp/test_default.db"


def test_empty_backend_is_sqlite(monkeypatch):
    """Empty STORAGE_BACKEND — get_db_path() works with sqlite."""
    monkeypatch.setenv("STORAGE_BACKEND", "")
    monkeypatch.setenv("APP_DB_PATH", "/tmp/test_empty.db")
    mod = _reload_storage()
    assert mod.get_db_path() == "/tmp/test_empty.db"


def test_sqlite_backend_is_sqlite(monkeypatch):
    """Explicit STORAGE_BACKEND=sqlite — works."""
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("APP_DB_PATH", "/tmp/test_sqlite.db")
    mod = _reload_storage()
    assert mod.get_db_path() == "/tmp/test_sqlite.db"


def test_unsupported_backend_raises_on_function_call(monkeypatch):
    """Import succeeds but calling a function raises ValueError."""
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    mod = _reload_storage()
    import pytest
    with pytest.raises(ValueError, match="dynamodb"):
        mod.get_db_path()
