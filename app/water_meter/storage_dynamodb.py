"""DynamoDB implementation for Water Meter readings storage.

Reuses the existing shared App Runner DynamoDB table.  Water Meter
items are separated from Broken Clock items via ``entity_type``.
"""

import os
import uuid
from datetime import datetime, timezone

from app.core.storage.dynamodb import get_dynamodb_table, query_all_items


APP_ID_DEFAULT = "articles-api"
ENTITY_TYPE = "water_meter"


def _table():
    """Convenience: return the DynamoDB table configured for Water Meter."""
    return get_dynamodb_table()


def _app_id():
    return os.environ.get("APP_ID", APP_ID_DEFAULT)


def get_db_path():
    """Return None — DynamoDB does not use a file path."""
    return None


def ensure_db_initialized(_db_path):
    """No-op — DynamoDB table is created by Terraform, not at runtime."""


def save_reading(_db_path, reading_value, reading_date,
                 meter_name="main", unit="m3", notes=""):
    """Insert a water meter reading into DynamoDB."""
    app_id = _app_id()
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    table = _table()
    table.put_item(Item={
        "id": uuid.uuid4().hex[:12],
        "app_id": app_id,
        "created_at": created_at,
        "entity_type": ENTITY_TYPE,
        "reading_date": reading_date,
        "meter_name": meter_name,
        "reading_value": reading_value,
        "unit": unit,
        "notes": notes,
    })


def get_readings(_db_path):
    """Return all water meter readings, newest first, with SQLite-compatible shape."""
    app_id = _app_id()
    table = _table()
    items = query_all_items(table, "app_id", app_id)

    rows = []
    for item in items:
        if item.get("entity_type") != ENTITY_TYPE:
            continue
        id_val = item.get("id", item["created_at"])
        rows.append({
            "id": id_val,
            "created_at": item["created_at"],
            "reading_date": item["reading_date"],
            "meter_name": item["meter_name"],
            "reading_value": item["reading_value"],
            "unit": item["unit"],
            "notes": item.get("notes", ""),
        })

    return rows


def get_meter_names(_db_path):
    """Return sorted distinct meter names from Water Meter items only."""
    app_id = _app_id()
    table = _table()
    items = query_all_items(table, "app_id", app_id)

    names = set()
    for item in items:
        if item.get("entity_type") != ENTITY_TYPE:
            continue
        name = item.get("meter_name", "").strip()
        if name:
            names.add(name)

    return sorted(names)


def delete_reading(record_id, _db_path):
    """Delete a Water Meter reading by stable id. Returns True if deleted, False if not found."""
    app_id = _app_id()
    table = _table()
    items = query_all_items(table, "app_id", app_id)

    target = None
    for item in items:
        if item.get("entity_type") != ENTITY_TYPE:
            continue
        if str(item.get("id", "")) == str(record_id):
            target = item
            break

    if target is None:
        return False

    table.delete_item(Key={
        "app_id": target["app_id"],
        "created_at": target["created_at"],
    })
    return True
