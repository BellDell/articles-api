"""SQLite implementation for Water Meter readings storage.

No Flask dependency. Shares the same database file as Broken Clock
via the APP_DB_PATH environment variable.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone


def get_db_path():
    """Return the database path from APP_DB_PATH env var or default."""
    return os.environ.get("APP_DB_PATH", "data/app.db")


def ensure_db_initialized(db_path):
    """Create the water_meter_readings table if missing.

    Idempotent — safe to call multiple times.
    """
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS water_meter_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                reading_date TEXT NOT NULL,
                meter_name TEXT NOT NULL,
                reading_value REAL NOT NULL,
                unit TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)
        conn.commit()


def save_reading(db_path, reading_value, reading_date,
                 meter_name="main", unit="m3", notes=""):
    """Insert a water meter reading into the database."""
    ensure_db_initialized(db_path)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """INSERT INTO water_meter_readings
               (created_at, reading_date, meter_name, reading_value, unit, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (created_at, reading_date, meter_name, reading_value, unit, notes),
        )
        conn.commit()


def get_readings(db_path):
    """Return all readings, newest first."""
    ensure_db_initialized(db_path)
    rows = []
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM water_meter_readings ORDER BY created_at DESC"
        )
        for row in cursor.fetchall():
            rows.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "reading_date": row["reading_date"],
                "meter_name": row["meter_name"],
                "reading_value": row["reading_value"],
                "unit": row["unit"],
                "notes": row["notes"] or "",
            })
    return rows


def get_meter_names(db_path):
    """Return sorted distinct meter names."""
    ensure_db_initialized(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.execute(
            "SELECT DISTINCT meter_name FROM water_meter_readings "
            "WHERE meter_name IS NOT NULL AND meter_name != '' "
            "ORDER BY meter_name"
        )
        return [row[0] for row in cursor.fetchall()]
