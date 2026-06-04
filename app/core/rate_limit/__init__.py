"""Write rate limiter facade.

Usage in routes::

    from app.core.rate_limit import consume_write_quota
    allowed, retry_after = consume_write_quota("broken_clock", request.remote_addr)
    if not allowed:
        return jsonify({...}), 429, {"Retry-After": str(retry_after)}
"""

import os


def _get_backend():
    backend = os.environ.get("STORAGE_BACKEND", "sqlite") or "sqlite"
    if backend == "sqlite":
        return "sqlite"
    elif backend == "dynamodb":
        return "dynamodb"
    raise ValueError(
        f"Unsupported STORAGE_BACKEND: {backend!r}. "
        f"Supported values: 'sqlite', 'dynamodb'."
    )


def consume_write_quota(feature_name, client_ip):
    """Check and consume a write quota.

    Returns (allowed: bool, retry_after: int).
    """
    backend = _get_backend()
    if backend == "dynamodb":
        from app.core.rate_limit.storage_dynamodb import consume_write_quota as _fn
    else:
        from app.core.rate_limit.storage_sqlite import consume_write_quota as _fn
    return _fn(feature_name, client_ip)
