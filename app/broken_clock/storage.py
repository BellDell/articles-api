"""Storage facade for Broken Clock Calculator history.

This module is the public API imported by routes. It delegates to the
appropriate backend implementation based on the STORAGE_BACKEND env var.
"""

import os


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
        from app.broken_clock.storage_dynamodb import get_db_path as _fn
    else:
        from app.broken_clock.storage_sqlite import get_db_path as _fn
    return _fn()


def ensure_db_initialized(db_path):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.broken_clock.storage_dynamodb import ensure_db_initialized as _fn
    else:
        from app.broken_clock.storage_sqlite import ensure_db_initialized as _fn
    return _fn(db_path)


def save_calculation(db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.broken_clock.storage_dynamodb import save_calculation as _fn
    else:
        from app.broken_clock.storage_sqlite import save_calculation as _fn
    return _fn(db_path, real_observed_time, wrong_observed_time,
               offset_minutes, offset_human, clock_status,
               target_wrong_times, reference_points)


def get_history(db_path):
    backend = _get_backend()
    if backend == "dynamodb":
        from app.broken_clock.storage_dynamodb import get_history as _fn
    else:
        from app.broken_clock.storage_sqlite import get_history as _fn
    return _fn(db_path)
