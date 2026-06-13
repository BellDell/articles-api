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


def _is_broken_clock_item(item):
    """Return True if the item is a Broken Clock record (not rate-limit or other)."""
    et = item.get("entity_type")
    # Legacy items have no entity_type; new items have "broken_clock"
    return et is None or et == "broken_clock"


def get_db_path():
    """Return None — DynamoDB does not use a file path."""
    return None


def ensure_db_initialized(_db_path):
    """No-op — DynamoDB table is created by Terraform, not at runtime."""


def save_calculation(_db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points,
                     owner_username=None, calc_date=None):
    """Insert a successful calculation into DynamoDB."""
    app_id = os.environ.get("APP_ID", APP_ID_DEFAULT)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    table = _table()
    item = {
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
        "calc_date": calc_date,
    }
    if owner_username:
        item["owner_username"] = owner_username
    table.put_item(Item=item)


def get_history(_db_path, owner_username=None):
    """Return saved calculations, newest first, with JSON fields decoded.

    If *owner_username* is set (and user is not admin), only return records
    owned by that user, excluding legacy unowned records.
    """
    from app.core.authz import is_admin
    items = _query_broken_clock_items()

    rows = []
    for item in items:
        if not _is_broken_clock_item(item):
            continue
        record_owner = item.get("owner_username")
        if owner_username and not is_admin(owner_username):
            # Normal user: only see owned records
            if not record_owner:
                continue
            if record_owner != owner_username:
                continue
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
            "calc_date": item.get("calc_date") or item["created_at"][:10],
        })

    return rows


def delete_history_record(record_id, _db_path, owner_username=None):
    """Delete a history record by stable id.

    If *owner_username* is set (and user is not admin), only delete if the
    record belongs to that user. Returns True if deleted, False if not found.
    """
    from app.core.authz import is_admin
    items = _query_broken_clock_items()
    table = _table()

    target = None
    for item in items:
        if not _is_broken_clock_item(item):
            continue
        item_id = item.get("id", item["created_at"])
        if str(item_id) == str(record_id):
            target = item
            break

    if target is None:
        return False

    # Ownership check for normal users
    if owner_username and not is_admin(owner_username):
        record_owner = target.get("owner_username")
        if not record_owner or record_owner != owner_username:
            return False

    table.delete_item(Key={
        "app_id": target["app_id"],
        "created_at": target["created_at"],
    })
    return True
