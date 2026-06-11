"""DynamoDB implementation for Water Meter readings storage.

Reuses the existing shared App Runner DynamoDB table.  Water Meter
items are separated from Broken Clock items via ``entity_type``.
"""

import os
import uuid
from decimal import Decimal
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
                 meter_name="main", unit="m3", notes="",
                 owner_username=None):
    """Insert a water meter reading into DynamoDB."""
    app_id = _app_id()
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reading_value_decimal = Decimal(str(reading_value))

    table = _table()
    item = {
        "id": uuid.uuid4().hex[:12],
        "app_id": app_id,
        "created_at": created_at,
        "entity_type": ENTITY_TYPE,
        "reading_date": reading_date,
        "meter_name": meter_name,
        "reading_value": reading_value_decimal,
        "unit": unit,
        "notes": notes,
    }
    if owner_username:
        item["owner_username"] = owner_username
    table.put_item(Item=item)


def get_readings(_db_path, owner_username=None):
    """Return water meter readings, newest first, with SQLite-compatible shape.

    If *owner_username* is set (and user is not admin), only return readings
    owned by that user, excluding legacy unowned records.
    """
    from app.core.authz import is_admin
    app_id = _app_id()
    table = _table()
    items = query_all_items(table, "app_id", app_id)

    rows = []
    for item in items:
        if item.get("entity_type") != ENTITY_TYPE:
            continue
        record_owner = item.get("owner_username")
        if owner_username and not is_admin(owner_username):
            if not record_owner:
                continue
            if record_owner != owner_username:
                continue
        id_val = item.get("id", item["created_at"])
        reading_value = item["reading_value"]
        if isinstance(reading_value, Decimal):
            reading_value = float(reading_value)
        rows.append({
            "id": id_val,
            "created_at": item["created_at"],
            "reading_date": item["reading_date"],
            "meter_name": item["meter_name"],
            "reading_value": reading_value,
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


def delete_reading(record_id, _db_path, owner_username=None):
    """Delete a Water Meter reading by stable id.

    If *owner_username* is set (and is not admin), only delete if the record
    belongs to that user. Returns True if deleted, False if not found.
    """
    from app.core.authz import is_admin
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
