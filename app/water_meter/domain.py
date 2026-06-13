"""Domain validation for water meter readings."""

import re
from datetime import date

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_reading(
    reading_value, reading_date, meter_name=None, unit=None, notes=None
):
    """Validate a water meter reading. Returns (errors_dict, cleaned_data).

    If validation passes, *errors* is an empty dict and *cleaned_data* contains
    the normalised input values.  If validation fails, *errors* maps field names
    to error messages and *cleaned_data* is ``None``.
    """
    errors = {}

    # reading_value — required, numeric, non-negative
    if reading_value is None or (isinstance(reading_value, str) and not reading_value.strip()):
        errors["reading_value"] = "Reading value is required."
    else:
        try:
            val = float(reading_value)
            if val < 0:
                errors["reading_value"] = "Reading value must be non-negative."
        except (ValueError, TypeError):
            errors["reading_value"] = "Reading value must be a number."

    # reading_date — required, YYYY-MM-DD
    if not reading_date or not isinstance(reading_date, str) or not reading_date.strip():
        errors["reading_date"] = "Reading date is required."
    elif not _DATE_RE.match(reading_date):
        errors["reading_date"] = "Reading date must be in YYYY-MM-DD format."

    if not errors.get("reading_date") and reading_date and reading_date.strip():
        try:
            parsed = date.fromisoformat(reading_date.strip())
            if parsed > date.today():
                errors["reading_date"] = "Reading date cannot be in the future."
        except ValueError:
            pass

    # Defaults for optional fields
    cleaned_meter_name = (meter_name or "").strip() or "main"
    cleaned_unit = (unit or "").strip() or "m3"
    cleaned_notes = (notes or "").strip()

    if errors:
        return errors, None

    return {}, {
        "reading_value": float(reading_value),
        "reading_date": reading_date.strip(),
        "meter_name": cleaned_meter_name,
        "unit": cleaned_unit,
        "notes": cleaned_notes,
    }
