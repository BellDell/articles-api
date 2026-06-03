"""Tests for broken_clock_storage backend selection."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_default_backend_is_sqlite(monkeypatch):
    """Missing STORAGE_BACKEND defaults to sqlite."""
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    # Re-import the module to trigger the backend check
    if "app.broken_clock_storage" in sys.modules:
        del sys.modules["app.broken_clock_storage"]
    import app.broken_clock_storage as mod
    assert mod._STORAGE_BACKEND == "sqlite"


def test_empty_backend_is_sqlite(monkeypatch):
    """Empty STORAGE_BACKEND maps to sqlite."""
    monkeypatch.setenv("STORAGE_BACKEND", "")
    if "app.broken_clock_storage" in sys.modules:
        del sys.modules["app.broken_clock_storage"]
    import app.broken_clock_storage as mod
    assert mod._STORAGE_BACKEND == "sqlite"


def test_sqlite_backend_is_sqlite(monkeypatch):
    """Explicit STORAGE_BACKEND=sqlite works."""
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    if "app.broken_clock_storage" in sys.modules:
        del sys.modules["app.broken_clock_storage"]
    import app.broken_clock_storage as mod
    assert mod._STORAGE_BACKEND == "sqlite"


def test_unsupported_backend_raises(monkeypatch):
    """Unsupported STORAGE_BACKEND raises ValueError."""
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    if "app.broken_clock_storage" in sys.modules:
        del sys.modules["app.broken_clock_storage"]
    import pytest
    with pytest.raises(ValueError, match="dynamodb"):
        import app.broken_clock_storage  # noqa: F811
