"""Storage facade for Broken Clock Calculator history.

This module is the public API imported by routes. It delegates to the
appropriate backend implementation based on the STORAGE_BACKEND env var.
Currently only sqlite is implemented.
"""

from app.broken_clock.storage_sqlite import (
    get_db_path,
    ensure_db_initialized,
    save_calculation,
    get_history,
)
