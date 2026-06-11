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
    Also migrates to add owner_username column if not present.
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
        # Idempotent migration: add owner_username if missing
        cursor = conn.execute("PRAGMA table_info(water_meter_readings)")
        columns = [row[1] for row in cursor.fetchall()]
        if "owner_username" not in columns:
            conn.execute("ALTER TABLE water_meter_readings ADD COLUMN owner_username TEXT")
        conn.commit()


def save_reading(db_path, reading_value, reading_date,
                 meter_name="main", unit="m3", notes="",
                 owner_username=None):
    """Insert a water meter reading into the database."""
    ensure_db_initialized(db_path)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """INSERT INTO water_meter_readings
               (created_at, reading_date, meter_name, reading_value, unit, notes,
                owner_username)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (created_at, reading_date, meter_name, reading_value, unit, notes,
             owner_username),
        )
        conn.commit()


def get_readings(db_path, owner_username=None):
    """Return readings, newest first.

    If *owner_username* is set (and user is not admin), only return readings
    owned by that user, excluding legacy unowned records.
    """
    from app.core.authz import is_admin
    ensure_db_initialized(db_path)
    rows = []
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        if owner_username and not is_admin(owner_username):
            cursor = conn.execute(
                "SELECT * FROM water_meter_readings "
                "WHERE owner_username = ? "
                "ORDER BY created_at DESC",
                (owner_username,),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM water_meter_readings ORDER BY created_at DESC"
            )
        for row in cursor.fetchall():
            # For normal users, skip legacy rows (NULL owner_username)
            if owner_username and not is_admin(owner_username):
                if row["owner_username"] is None:
                    continue
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


def delete_reading(record_id, db_path, owner_username=None):
    """Delete a reading by id.

    If *owner_username* is set (and is not admin), only delete if the record
    belongs to that user. Returns True if deleted, False if not found.
    """
    from app.core.authz import is_admin
    ensure_db_initialized(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        if owner_username and not is_admin(owner_username):
            cursor = conn.execute(
                "DELETE FROM water_meter_readings WHERE id = ? AND owner_username = ?",
                (record_id, owner_username),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM water_meter_readings WHERE id = ?",
                (record_id,),
            )
        conn.commit()
        return cursor.rowcount > 0
