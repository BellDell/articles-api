"""SQLite storage helpers for Broken Clock Calculator history.

This module has no Flask dependency. It manages the APP_DB_PATH,
database initialization, and CRUD operations for calculation history.
"""

import os
import sqlite3
import json
from contextlib import closing
from datetime import datetime, timezone


def get_db_path():
    """Return the database path from APP_DB_PATH env var or default."""
    return os.environ.get("APP_DB_PATH", "data/app.db")


def ensure_db_initialized(db_path):
    """Create the data directory and broken_clock_history table if missing.

    Idempotent — safe to call multiple times.
    """
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broken_clock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                real_observed_time TEXT NOT NULL,
                wrong_observed_time TEXT NOT NULL,
                offset_minutes INTEGER NOT NULL,
                offset_human TEXT NOT NULL,
                clock_status TEXT NOT NULL,
                target_wrong_times_json TEXT NOT NULL,
                reference_points_json TEXT NOT NULL
            )
        """)
        conn.commit()


def save_calculation(db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points):
    """Insert a successful calculation into the history table."""
    ensure_db_initialized(db_path)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """INSERT INTO broken_clock_history
               (created_at, real_observed_time, wrong_observed_time,
                offset_minutes, offset_human, clock_status,
                target_wrong_times_json, reference_points_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (created_at, real_observed_time, wrong_observed_time,
             offset_minutes, offset_human, clock_status,
             json.dumps(target_wrong_times), json.dumps(reference_points))
        )
        conn.commit()


def get_history(db_path):
    """Return all saved calculations, newest first, with JSON fields decoded."""
    ensure_db_initialized(db_path)
    rows = []
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM broken_clock_history ORDER BY created_at DESC"
        )
        for row in cursor.fetchall():
            rows.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "real_observed_time": row["real_observed_time"],
                "wrong_observed_time": row["wrong_observed_time"],
                "offset_minutes": row["offset_minutes"],
                "offset_human": row["offset_human"],
                "clock_status": row["clock_status"],
                "target_wrong_times": json.loads(row["target_wrong_times_json"]),
                "reference_points": json.loads(row["reference_points_json"]),
            })
    return rows


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

_STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "sqlite") or "sqlite"
if _STORAGE_BACKEND != "sqlite":
    raise ValueError(
        f"Unsupported STORAGE_BACKEND: {_STORAGE_BACKEND!r}. "
        f"Only 'sqlite' is implemented."
    )
