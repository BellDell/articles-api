"""Storage facade for Water Meter readings.

Dispatches to SQLite or DynamoDB based on the STORAGE_BACKEND env var.
SQLite is the default.
"""

import os


def _get_backend():
    backend = os.environ.get("STORAGE_BACKEND", "sqlite") or "sqlite"
    if backend == "sqlite":
        return "sqlite"
    elif backend == "dynamodb":
        return "dynamodb"
    raise ValueError(
        f"Unsupported STORAGE_BACKEND: {backend!r}. "
        f"Supported values: 'sqlite', 'dynamodb'."
    )


def get_db_path():
    backend = _get_backend()
    if backend == "dynamodb":
        from app.water_meter.storage_dynamodb import get_db_path as _fn
    else:
        from app.water_meter.storage_sqlite import get_db_path as _fn
    return _fn()


def ensure_db_initialized(db_path):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.water_meter.storage_dynamodb import ensure_db_initialized as _fn
    else:
        from app.water_meter.storage_sqlite import ensure_db_initialized as _fn
    return _fn(db_path)


def save_reading(db_path, reading_value, reading_date,
                 meter_name="main", unit="m3", notes=""):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.water_meter.storage_dynamodb import save_reading as _fn
    else:
        from app.water_meter.storage_sqlite import save_reading as _fn
    return _fn(db_path, reading_value, reading_date,
               meter_name=meter_name, unit=unit, notes=notes)


def get_readings(db_path):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.water_meter.storage_dynamodb import get_readings as _fn
    else:
        from app.water_meter.storage_sqlite import get_readings as _fn
    return _fn(db_path)


def get_meter_names(db_path):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.water_meter.storage_dynamodb import get_meter_names as _fn
    else:
        from app.water_meter.storage_sqlite import get_meter_names as _fn
    return _fn(db_path)
