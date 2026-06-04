"""DynamoDB implementation for Broken Clock Calculator history storage.

This module contains Broken Clock-specific mapping — item shape for
save, history response shape, and delete-by-stable-id logic.  Generic
DynamoDB plumbing (table lookup, pagination) lives in
:mod:`app.core.storage.dynamodb`.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from app.core.storage.dynamodb import (
    get_dynamodb_table,
    query_all_items,
)


APP_ID_DEFAULT = "articles-api"


def _table():
    """Convenience: return the DynamoDB table configured for Broken Clock."""
    return get_dynamodb_table()


def _query_broken_clock_items():
    """Return all DynamoDB items for the current Broken Clock APP_ID, newest first."""
    app_id = os.environ.get("APP_ID", APP_ID_DEFAULT)
    table = _table()
    return query_all_items(table, "app_id", app_id)


def get_db_path():
    """Return None — DynamoDB does not use a file path."""
    return None


def ensure_db_initialized(_db_path):
    """No-op — DynamoDB table is created by Terraform, not at runtime."""


def save_calculation(_db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points):
    """Insert a successful calculation into DynamoDB."""
    app_id = os.environ.get("APP_ID", APP_ID_DEFAULT)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    table = _table()
    table.put_item(Item={
        "id": uuid.uuid4().hex[:12],
        "app_id": app_id,
        "created_at": created_at,
        "real_observed_time": real_observed_time,
        "wrong_observed_time": wrong_observed_time,
        "offset_minutes": offset_minutes,
        "offset_human": offset_human,
        "clock_status": clock_status,
        "target_wrong_times": json.dumps(target_wrong_times),
        "reference_points": json.dumps(reference_points),
    })


def get_history(_db_path):
    """Return all saved calculations, newest first, with JSON fields decoded."""
    items = _query_broken_clock_items()

    rows = []
    for item in items:
        rows.append({
            "id": item.get("id", item["created_at"]),
            "created_at": item["created_at"],
            "real_observed_time": item["real_observed_time"],
            "wrong_observed_time": item["wrong_observed_time"],
            "offset_minutes": item["offset_minutes"],
            "offset_human": item["offset_human"],
            "clock_status": item["clock_status"],
            "target_wrong_times": json.loads(item["target_wrong_times"]),
            "reference_points": json.loads(item["reference_points"]),
        })

    return rows


def delete_history_record(record_id, _db_path):
    """Delete a history record by stable id. Returns True if deleted, False if not found."""
    items = _query_broken_clock_items()
    table = _table()

    target = None
    for item in items:
        item_id = item.get("id", item["created_at"])
        if str(item_id) == str(record_id):
            target = item
            break

    if target is None:
        return False

    table.delete_item(Key={
        "app_id": target["app_id"],
        "created_at": target["created_at"],
    })
    return True
