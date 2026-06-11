"""SQLite implementation for auth user storage.

This module has no Flask dependency. It manages user records in SQLite
using the APP_DB_PATH environment variable.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from app.auth.storage import DuplicateUserError


def get_db_path():
    """Return the database path from APP_DB_PATH env var or default."""
    return os.environ.get("APP_DB_PATH", "data/app.db")


def ensure_db_initialized(db_path):
    """Create the data directory and auth_users table if missing.

    Idempotent — safe to call multiple times.
    """
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_users (
                username_canonical TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def create_user(db_path, username_canonical, password):
    """Create a new user. Returns the created_at timestamp.

    Translates sqlite3.IntegrityError to DuplicateUserError for duplicate
    username.

    Raises DuplicateUserError if username_canonical already exists.
    """
    ensure_db_initialized(db_path)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    password_hash = generate_password_hash(password)
    with closing(sqlite3.connect(db_path)) as conn:
        try:
            conn.execute(
                "INSERT INTO auth_users (username_canonical, password_hash, created_at) "
                "VALUES (?, ?, ?)",
                (username_canonical, password_hash, created_at),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise DuplicateUserError(f"User '{username_canonical}' already exists") from None
    return created_at


def get_user_by_username(db_path, username_canonical):
    """Return the user dict or None if not found.

    Returns None — never raises for missing user.
    """
    ensure_db_initialized(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM auth_users WHERE username_canonical = ?",
            (username_canonical,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "username_canonical": row["username_canonical"],
            "password_hash": row["password_hash"],
            "created_at": row["created_at"],
        }


def verify_user_password(db_path, username_canonical, password):
    """Return True if the username exists and password matches."""
    user = get_user_by_username(db_path, username_canonical)
    if user is None:
        return False
    return check_password_hash(user["password_hash"], password)


def list_users(db_path):
    """Return list of user dicts with username_canonical and created_at.

    Does NOT return password_hash. Uses a SELECT that explicitly omits it,
    rather than returning all columns and then stripping.
    """
    ensure_db_initialized(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT username_canonical, created_at FROM auth_users ORDER BY created_at ASC"
        )
        return [dict(row) for row in cursor.fetchall()]
