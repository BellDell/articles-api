"""DynamoDB implementation for the write rate limiter.

Reuses the existing shared App Runner DynamoDB table.
Uses atomic conditional updates for correctness.
"""

import os
import time

from app.core.storage.dynamodb import get_dynamodb_table
from app.core.rate_limit.limiter import (
    WINDOW_SECONDS,
    MAX_WRITES,
    ip_hash,
    current_window_start,
    retry_after_seconds,
)

APP_ID_DEFAULT = "articles-api"
ENTITY_TYPE = "rate_limit"


def _app_id():
    return os.environ.get("APP_ID", APP_ID_DEFAULT)


def _bucket_key(feature_name, client_ip):
    """Return the deterministic sort key for a rate-limit bucket."""
    ip_h = ip_hash(client_ip)
    wstart = current_window_start()
    return f"rate_limit#{feature_name}#{ip_h}#{wstart}"


def consume_write_quota(feature_name, client_ip):
    """Check and consume a write quota. Returns (allowed: bool, retry_after: int).

    Uses an atomic DynamoDB conditional update to increment a counter.
    If the item does not exist, it is created with counter = 1.
    If the counter is already >= MAX_WRITES, the update is rejected.
    """
    table = get_dynamodb_table()
    app_id = _app_id()
    bucket = _bucket_key(feature_name, client_ip)

    try:
        table.update_item(
            Key={"app_id": app_id, "created_at": bucket},
            UpdateExpression="ADD #cnt :inc SET #et = :et",
            ConditionExpression="attribute_not_exists(#cnt) OR #cnt < :max",
            ExpressionAttributeNames={"#cnt": "counter", "#et": "entity_type"},
            ExpressionAttributeValues={
                ":inc": 1,
                ":max": MAX_WRITES,
                ":et": ENTITY_TYPE,
            },
        )
        return True, 0
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return False, retry_after_seconds(int(time.time()))
    except Exception:
        # If the table doesn't exist or other error, let it propagate
        raise
