"""Storage facade for auth user storage.

This module is the public API imported by routes. It delegates to the
appropriate backend implementation based on the STORAGE_BACKEND env var.

Routes should NOT call get_db_path() directly. The facade handles
backend dispatch internally.
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


def create_user(username_canonical, password):
    """Create a new user. Returns the created_at timestamp.

    Raises DuplicateUserError if username_canonical already exists.
    """
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import create_user as _fn
        return _fn(None, username_canonical, password)
    else:
        from app.auth.storage_sqlite import create_user as _fn
        from app.auth.storage_sqlite import get_db_path as _db
        return _fn(_db(), username_canonical, password)


def get_user_by_username(username_canonical):
    """Return the user dict or None if not found."""
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import get_user_by_username as _fn
        return _fn(None, username_canonical)
    else:
        from app.auth.storage_sqlite import get_user_by_username as _fn
        from app.auth.storage_sqlite import get_db_path as _db
        return _fn(_db(), username_canonical)


def verify_user_password(username_canonical, password):
    """Return True if the username exists and password matches."""
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import verify_user_password as _fn
        return _fn(None, username_canonical, password)
    else:
        from app.auth.storage_sqlite import verify_user_password as _fn
        from app.auth.storage_sqlite import get_db_path as _db
        return _fn(_db(), username_canonical, password)


def get_db_path():
    """Return the SQLite database path.

    Raises RuntimeError when STORAGE_BACKEND=dynamodb because DynamoDB
    does not use a local db path. Routes should not call get_db_path()
    for auth storage — use facade functions like create_user or
    get_user_by_username instead.
    """
    backend = _get_backend()
    if backend == "dynamodb":
        raise RuntimeError(
            "auth_storage.get_db_path() is not available with STORAGE_BACKEND=dynamodb. "
            "Use auth_storage.create_user() and auth_storage.get_user_by_username() instead."
        )
    from app.auth.storage_sqlite import get_db_path as _fn
    return _fn()


def list_users():
    """Return a list of user dicts with username_canonical and created_at.

    Does NOT return password_hash. Backend-neutral — delegates to
    SQLite or DynamoDB based on STORAGE_BACKEND.
    """
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import list_users as _fn
        return _fn(None)
    else:
        from app.auth.storage_sqlite import list_users as _fn
        from app.auth.storage_sqlite import get_db_path as _db
        return _fn(_db())
