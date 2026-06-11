"""Authorization helpers: route protection, user extraction, ownership checks."""

import os
from functools import wraps

from flask import g, redirect, request, url_for


# ---------------------------------------------------------------------------
# Route authorization map — single source of truth
# ---------------------------------------------------------------------------
# Keyed by Flask endpoint name (from app.url_map).  Update these only when
# adding/changing routes that need protection.  The runtime test in
# tests/test_authorization.py iterates app.url_map and fails on drift.

PUBLIC_ENDPOINTS = frozenset({
    "home",
    "health",
    "auth_login_get",
    "auth_login_post",
    "auth_register_get",
    "auth_register_post",
    "auth_logout",
    "auth_me",
    "static",
    "get_authors",
    "get_articles",
    "get_author",
    "get_article",
})

PROTECTED_ENDPOINT_MODES = {
    # Broken Clock
    "broken_clock_form": "html",
    "broken_clock_calculate": "json",
    "broken_clock_history": "html",
    "delete_history": "json",
    "delete_history_html": "json",
    # Water Meter
    "water_meter_form": "html",
    "water_meter_add_reading": "json",
    "water_meter_history": "html",
    "delete_water_meter_reading": "json",
    "delete_water_meter_reading_html": "json",
}


# ---------------------------------------------------------------------------
# Username canonicalization
# ---------------------------------------------------------------------------

def canonicalize_username(value):
    """Normalize a username to canonical form: strip whitespace and casefold."""
    return value.strip().casefold()


# ---------------------------------------------------------------------------
# Current user extraction
# ---------------------------------------------------------------------------

def get_current_username():
    """Return the canonical username from the JWT cookie, or None.

    Returns None for missing/invalid/expired tokens.
    Does not leak token data.
    """
    from app.auth.jwt import verify_token
    token = request.cookies.get("access_token")
    if not token:
        return None
    username = verify_token(token)
    if not username:
        return None
    return canonicalize_username(username)


def get_current_username_or_redirect():
    """Return canonical username or redirect to login page for HTML requests.

    For anonymous HTML requests: redirects to /auth/login.
    For anonymous JSON requests: returns None (caller handles 401).
    """
    username = get_current_username()
    if username:
        g.current_username = username
        return username
    if request.is_json or request.accept_mimetypes.accept_json:
        return None
    # Browser HTML request
    return None  # caller must check and redirect


# ---------------------------------------------------------------------------
# login_required decorator
# ---------------------------------------------------------------------------

def login_required(mode="html"):
    """Decorator that protects a route with authentication.

    Parameters
    ----------
    mode : str
        "html" — anonymous requests redirect to /auth/login.
        "json" — anonymous requests return HTTP 401.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            username = get_current_username()
            if not username:
                if mode == "html":
                    return redirect(url_for("auth_login_get"))
                return {"error": "Authentication required"}, 401
            g.current_username = username
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Ownership helpers
# ---------------------------------------------------------------------------

def is_admin(username):
    """Return True if *username* is in AUTH_ADMIN_USERS.

    AUTH_ADMIN_USERS is a comma-separated list of canonical usernames.
    Missing or empty means no admins.
    """
    raw = os.environ.get("AUTH_ADMIN_USERS", "")
    if not raw.strip():
        return False
    admins = [canonicalize_username(a) for a in raw.split(",") if a.strip()]
    return username in admins


def authorize_ownership(record_owner_username, current_username):
    """Return True if *current_username* can access/delete the record.

    *record_owner_username* may be None for legacy records.
    """
    if current_username is None:
        return False
    if record_owner_username is None:
        # Legacy record — only admins
        return is_admin(current_username)
    if record_owner_username == current_username:
        return True
    return is_admin(current_username)
