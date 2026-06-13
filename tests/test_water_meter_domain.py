"""Tests for water meter domain validation."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.water_meter.domain import validate_reading


def test_valid_input():
    errors, cleaned = validate_reading(123.45, "2026-06-01", meter_name="kitchen", unit="m3", notes="monthly")
    assert errors == {}
    assert cleaned["reading_value"] == 123.45
    assert cleaned["reading_date"] == "2026-06-01"
    assert cleaned["meter_name"] == "kitchen"
    assert cleaned["unit"] == "m3"
    assert cleaned["notes"] == "monthly"


def test_missing_value():
    errors, _ = validate_reading("", "2026-06-01")
    assert "reading_value" in errors


def test_negative_value():
    errors, _ = validate_reading(-5, "2026-06-01")
    assert "reading_value" in errors


def test_non_numeric_value():
    errors, _ = validate_reading("abc", "2026-06-01")
    assert "reading_value" in errors


def test_missing_date():
    errors, _ = validate_reading(100, "")
    assert "reading_date" in errors


def test_invalid_date_format():
    errors, _ = validate_reading(100, "01-06-2026")
    assert "reading_date" in errors


def test_default_meter_name():
    _, cleaned = validate_reading(100, "2026-06-01", meter_name="")
    assert cleaned["meter_name"] == "main"


def test_default_unit():
    _, cleaned = validate_reading(100, "2026-06-01", unit="")
    assert cleaned["unit"] == "m3"


def test_notes_optional():
    _, cleaned = validate_reading(100, "2026-06-01")
    assert cleaned["notes"] == ""


def test_meter_name_default_when_none():
    _, cleaned = validate_reading(100, "2026-06-01", meter_name=None)
    assert cleaned["meter_name"] == "main"


# ---------------------------------------------------------------------------
# Future-date validation tests
# ---------------------------------------------------------------------------

def test_future_date_rejected():
    """A future reading_date returns a reading_date error."""
    errors, _ = validate_reading(100, "2099-12-31")
    assert "reading_date" in errors
    assert errors["reading_date"] == "Reading date cannot be in the future."


def test_today_date_accepted():
    """Today's date is accepted."""
    from datetime import date
    today = date.today().isoformat()
    errors, cleaned = validate_reading(100, today)
    assert errors == {}
    assert cleaned["reading_date"] == today


def test_past_date_accepted():
    """A past date is accepted."""
    errors, cleaned = validate_reading(100, "2020-01-01")
    assert errors == {}
    assert cleaned["reading_date"] == "2020-01-01"


def test_invalid_date_format_skips_future_check():
    """A date that fails format check is caught before the future-date check."""
    errors, _ = validate_reading(100, "not-a-date")
    assert "reading_date" in errors
    assert errors["reading_date"] == "Reading date must be in YYYY-MM-DD format."
