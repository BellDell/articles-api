"""Shared constants and helpers for rate limiting."""

import hashlib

WINDOW_SECONDS = 43200  # 12 hours
MAX_WRITES = 5


def ip_hash(client_ip):
    """Return a short SHA-256 hex digest of the client IP.

    The raw IP is never stored in the database — only the hash.
    """
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:16]


def current_window_start(now_epoch=None):
    """Return the start of the current fixed 12-hour window (epoch seconds)."""
    import time
    if now_epoch is None:
        now_epoch = int(time.time())
    return (now_epoch // WINDOW_SECONDS) * WINDOW_SECONDS


def retry_after_seconds(now_epoch=None):
    """Return seconds until the end of the current fixed window."""
    import time
    if now_epoch is None:
        now_epoch = int(time.time())
    window_start = current_window_start(now_epoch)
    return (window_start + WINDOW_SECONDS) - now_epoch


def make_429_response():
    """Return a (dict, status_code, headers) tuple for a 429 response."""
    from flask import jsonify
    secs = retry_after_seconds()
    body = {
        "error": "Rate limit exceeded. Try again later.",
    }
    return jsonify(body), 429, {"Retry-After": str(secs)}
