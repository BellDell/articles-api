"""DynamoDB implementation for auth user storage.

Reuses the existing shared DynamoDB table and key schema.
Auth users use entity_type = "auth_user" and a deterministic
sort key of "auth_user#<username_canonical>".
"""

import os
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from app.auth.storage import DuplicateUserError
from app.core.storage.dynamodb import get_dynamodb_table

APP_ID_DEFAULT = "articles-api"


def _table():
    """Return the DynamoDB table resource (lazy boto3 import)."""
    return get_dynamodb_table()


def _app_id():
    return os.environ.get("APP_ID", APP_ID_DEFAULT)


def _sort_key(username_canonical):
    return f"auth_user#{username_canonical}"


def create_user(_db_path, username_canonical, password):
    """Create a new auth user. Uses conditional PutItem for atomicity.

    Translates ConditionalCheckFailedException to DuplicateUserError.
    Re-raises other ClientError / unexpected exceptions.
    """
    password_hash = generate_password_hash(password)
    registered_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    app_id = _app_id()
    sk = _sort_key(username_canonical)

    table = _table()
    try:
        table.put_item(
            Item={
                "app_id": app_id,
                "created_at": sk,
                "entity_type": "auth_user",
                "username": username_canonical,
                "password_hash": password_hash,
                "registered_at": registered_at,
            },
            ConditionExpression="attribute_not_exists(created_at)",
        )
    except _client_error() as e:
        code = e.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise DuplicateUserError(f"User '{username_canonical}' already exists") from None
        raise
    return registered_at


def _client_error():
    """Return botocore ClientError exception class (lazy import)."""
    from botocore.exceptions import ClientError
    return ClientError


def get_user_by_username(_db_path, username_canonical):
    """Return the user dict or None if not found.

    Uses GetItem with the deterministic key — no Scan, no Query filtering.
    """
    app_id = _app_id()
    sk = _sort_key(username_canonical)

    table = _table()
    response = table.get_item(Key={"app_id": app_id, "created_at": sk})
    item = response.get("Item")
    if item is None:
        return None
    return {
        "username_canonical": item["username"],
        "password_hash": item["password_hash"],
        "created_at": item.get("registered_at", item["created_at"]),
    }


def verify_user_password(_db_path, username_canonical, password):
    """Return True if the username exists and password matches."""
    user = get_user_by_username(_db_path, username_canonical)
    if user is None:
        return False
    return check_password_hash(user["password_hash"], password)
