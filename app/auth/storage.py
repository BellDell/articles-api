"""Storage facade for auth user storage.

This module is the public API imported by routes. It delegates to the
appropriate backend implementation based on the STORAGE_BACKEND env var.
"""

import os


class DuplicateUserError(Exception):
    """Raised when attempting to create a user with an existing username."""
    pass


def _get_backend():
    """Return 'sqlite' or 'dynamodb' based on STORAGE_BACKEND env var."""
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
        from app.auth.storage_dynamodb import get_db_path as _fn
    else:
        from app.auth.storage_sqlite import get_db_path as _fn
    return _fn()


def create_user(db_path, username_canonical, password):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import create_user as _fn
    else:
        from app.auth.storage_sqlite import create_user as _fn
    return _fn(db_path, username_canonical, password)


def get_user_by_username(db_path, username_canonical):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import get_user_by_username as _fn
    else:
        from app.auth.storage_sqlite import get_user_by_username as _fn
    return _fn(db_path, username_canonical)


def verify_user_password(db_path, username_canonical, password):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import verify_user_password as _fn
    else:
        from app.auth.storage_sqlite import verify_user_password as _fn
    return _fn(db_path, username_canonical, password)
