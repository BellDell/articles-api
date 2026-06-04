"""Tests for Water Meter SQLite storage."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.water_meter import storage_sqlite as mod


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_wm.db")
    return path


def test_save_and_get_readings(db_path):
    mod.save_reading(db_path, 123.45, "2026-06-01", meter_name="kitchen", unit="m3", notes="monthly")
    mod.save_reading(db_path, 100.0, "2026-05-01")
    readings = mod.get_readings(db_path)
    assert len(readings) == 2
    # Newest first
    assert readings[0]["reading_value"] == 123.45
    assert readings[1]["reading_value"] == 100.0


def test_get_readings_empty(db_path):
    readings = mod.get_readings(db_path)
    assert readings == []


def test_save_reading_returns_nothing(db_path):
    result = mod.save_reading(db_path, 50, "2026-07-01")
    assert result is None


def test_defaults_stored(db_path):
    mod.save_reading(db_path, 100, "2026-06-01")
    readings = mod.get_readings(db_path)
    r = readings[0]
    assert r["meter_name"] == "main"
    assert r["unit"] == "m3"
    assert r["notes"] == ""
