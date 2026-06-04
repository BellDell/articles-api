"""SQLite implementation for the write rate limiter.

Uses the same APP_DB_PATH as the rest of the application.
Creates a ``rate_limit_windows`` table lazily.
"""

import os
import time
import sqlite3
from contextlib import closing

from app.core.rate_limit.limiter import (
    WINDOW_SECONDS,
    MAX_WRITES,
    ip_hash,
    current_window_start,
    retry_after_seconds,
)


def get_db_path():
    return os.environ.get("APP_DB_PATH", "data/app.db")


def _ensure_table(db_path):
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_windows (
                feature_name TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                window_start INTEGER NOT NULL,
                counter INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (feature_name, ip_hash, window_start)
            )
        """)
        conn.commit()


def consume_write_quota(feature_name, client_ip):
    """Check and consume a write quota. Returns (allowed: bool, retry_after: int)."""
    db_path = get_db_path()
    _ensure_table(db_path)

    ip_h = ip_hash(client_ip)
    now = int(time.time())
    wstart = current_window_start(now)

    with closing(sqlite3.connect(db_path)) as conn:
        # Read current counter
        cursor = conn.execute(
            "SELECT counter FROM rate_limit_windows "
            "WHERE feature_name = ? AND ip_hash = ? AND window_start = ?",
            (feature_name, ip_h, wstart),
        )
        row = cursor.fetchone()

        if row is None:
            # First write in this window — insert with counter 1
            conn.execute(
                "INSERT INTO rate_limit_windows (feature_name, ip_hash, window_start, counter) "
                "VALUES (?, ?, ?, 1)",
                (feature_name, ip_h, wstart),
            )
            conn.commit()
            return True, 0
        elif row[0] < MAX_WRITES:
            # Within limit — increment
            conn.execute(
                "UPDATE rate_limit_windows SET counter = counter + 1 "
                "WHERE feature_name = ? AND ip_hash = ? AND window_start = ?",
                (feature_name, ip_h, wstart),
            )
            conn.commit()
            return True, 0
        else:
            # Over limit
            conn.commit()
            return False, retry_after_seconds(now)
