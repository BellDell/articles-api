"""JWT helper functions for issuing and verifying access tokens."""

import os
from datetime import datetime, timedelta, timezone

import jwt


class MissingJwtSecretError(RuntimeError):
    """Raised when JWT_SECRET_KEY is missing, empty, or whitespace-only."""
    pass


def _get_secret():
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if not secret or not secret.strip():
        raise MissingJwtSecretError("JWT_SECRET_KEY is required")
    return secret


def issue_token(username, expires_in=86400):
    """Issue a signed JWT access token for the given username.

    Args:
        username: The subject of the token.
        expires_in: Token lifetime in seconds (default 24 hours).

    Returns:
        A signed JWT string.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def verify_token(token):
    """Verify a JWT access token and return the username.

    Args:
        token: The JWT string to verify.

    Returns:
        The username (str) if the token is valid, or None if
        the token is expired, malformed, or has a bad signature.
    """
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
