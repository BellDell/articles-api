"""Storage facade for Water Meter readings.

Currently SQLite only.  Routes import from this module.
"""

from app.water_meter.storage_sqlite import (
    get_db_path,
    ensure_db_initialized,
    save_reading,
    get_readings,
)
