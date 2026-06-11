"""SQLite implementation for Broken Clock Calculator history storage.

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
    Also migrates to add owner_username column if not present.
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
        # Idempotent migration: add owner_username if missing
        cursor = conn.execute("PRAGMA table_info(broken_clock_history)")
        columns = [row[1] for row in cursor.fetchall()]
        if "owner_username" not in columns:
            conn.execute("ALTER TABLE broken_clock_history ADD COLUMN owner_username TEXT")
        conn.commit()


def save_calculation(db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points,
                     owner_username=None):
    """Insert a successful calculation into the history table."""
    ensure_db_initialized(db_path)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """INSERT INTO broken_clock_history
               (created_at, real_observed_time, wrong_observed_time,
                offset_minutes, offset_human, clock_status,
                target_wrong_times_json, reference_points_json,
                owner_username)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (created_at, real_observed_time, wrong_observed_time,
             offset_minutes, offset_human, clock_status,
             json.dumps(target_wrong_times), json.dumps(reference_points),
             owner_username)
        )
        conn.commit()


def get_history(db_path, owner_username=None):
    """Return saved calculations, newest first, with JSON fields decoded.

    If *owner_username* is set, only return records for that user
    (and legacy records if the user is admin).
    """
    from app.core.authz import is_admin
    ensure_db_initialized(db_path)
    rows = []
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        if owner_username and not is_admin(owner_username):
            cursor = conn.execute(
                "SELECT * FROM broken_clock_history "
                "WHERE owner_username = ? "
                "ORDER BY created_at DESC",
                (owner_username,),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM broken_clock_history ORDER BY created_at DESC"
            )
        for row in cursor.fetchall():
            # For normal users, skip legacy rows (NULL owner_username)
            if owner_username and not is_admin(owner_username):
                if row["owner_username"] is None:
                    continue
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


def delete_history_record(record_id, db_path, owner_username=None):
    """Delete a history record by id.

    If *owner_username* is set (and is not admin), only delete if the record
    belongs to that user. Returns True if deleted, False if not found.
    """
    from app.core.authz import is_admin
    ensure_db_initialized(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        if owner_username and not is_admin(owner_username):
            cursor = conn.execute(
                "DELETE FROM broken_clock_history WHERE id = ? AND owner_username = ?",
                (record_id, owner_username),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM broken_clock_history WHERE id = ?",
                (record_id,),
            )
        conn.commit()
        return cursor.rowcount > 0
