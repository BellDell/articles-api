"""Tests for Water Meter DynamoDB storage backend."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from decimal import Decimal


class FakeTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)

    def query(self, KeyConditionExpression, ExpressionAttributeValues,
              ScanIndexForward, ExclusiveStartKey=None):
        expected_aid = ExpressionAttributeValues.get(":hv")
        matching = [it for it in self.items if it.get("app_id") == expected_aid]
        matching.sort(key=lambda it: it.get("created_at", ""), reverse=True)
        return {"Items": matching}

    def delete_item(self, Key):
        self.items = [it for it in self.items
                      if not (it.get("app_id") == Key.get("app_id")
                              and it.get("created_at") == Key.get("created_at"))]


class FakeDynamoDB:
    def __init__(self):
        self._tables = {}

    def Table(self, name):
        if name not in self._tables:
            self._tables[name] = FakeTable()
        return self._tables[name]


def _reload_wm_dynamodb():
    for key in list(sys.modules.keys()):
        if "water_meter.storage_dynamodb" in key:
            del sys.modules[key]
    import app.water_meter.storage_dynamodb as mod
    return mod


def test_save_writes_entity_type(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    mod.save_reading(None, 123.45, "2026-06-01")

    table = fake_db.Table("test-table")
    assert len(table.items) == 1
    item = table.items[0]
    assert item["entity_type"] == "water_meter"
    assert len(item["id"]) == 12


def test_save_writes_all_fields(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    mod.save_reading(None, 50.0, "2026-07-01", meter_name="garden", unit="gallons", notes="weekly")

    item = fake_db.Table("test-table").items[0]
    assert item["reading_value"] == Decimal("50.0")
    assert item["reading_date"] == "2026-07-01"
    assert item["meter_name"] == "garden"
    assert item["unit"] == "gallons"
    assert item["notes"] == "weekly"
    assert item["app_id"] == "test-app"
    assert "created_at" in item


def test_save_stores_reading_value_as_decimal(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    mod.save_reading(None, 123.45, "2026-06-01")

    item = fake_db.Table("test-table").items[0]
    assert item["reading_value"] == Decimal("123.45")
    assert not isinstance(item["reading_value"], float)


def test_get_readings_returns_only_water_meter(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")

    # Water Meter item
    table.put_item(Item={
        "id": "wm001",
        "app_id": "test-app",
        "created_at": "2026-06-01T12:00:00Z",
        "entity_type": "water_meter",
        "reading_date": "2026-06-01",
        "meter_name": "main",
        "reading_value": Decimal("100.0"),
        "unit": "m3",
        "notes": "",
    })
    # Broken Clock item
    table.put_item(Item={
        "id": "bc001",
        "app_id": "test-app",
        "created_at": "2026-05-01T12:00:00Z",
        "entity_type": "broken_clock",
        "real_observed_time": "10:00",
        "wrong_observed_time": "11:00",
    })
    # Legacy item without entity_type
    table.put_item(Item={
        "id": "legacy",
        "app_id": "test-app",
        "created_at": "2026-04-01T12:00:00Z",
        "real_observed_time": "09:00",
        "wrong_observed_time": "10:00",
    })

    readings = mod.get_readings(None)
    assert len(readings) == 1
    assert readings[0]["id"] == "wm001"
    assert readings[0]["reading_value"] == 100.0


def test_get_readings_newest_first(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    table.put_item(Item={
        "id": "wm_old",
        "app_id": "test-app",
        "created_at": "2026-01-01T10:00:00Z",
        "entity_type": "water_meter",
        "reading_date": "2026-01-01",
        "meter_name": "main",
        "reading_value": Decimal("100.0"),
        "unit": "m3",
        "notes": "",
    })
    table.put_item(Item={
        "id": "wm_new",
        "app_id": "test-app",
        "created_at": "2026-06-01T10:00:00Z",
        "entity_type": "water_meter",
        "reading_date": "2026-06-01",
        "meter_name": "main",
        "reading_value": Decimal("200.0"),
        "unit": "m3",
        "notes": "",
    })

    readings = mod.get_readings(None)
    assert len(readings) == 2
    assert readings[0]["id"] == "wm_new"
    assert readings[1]["id"] == "wm_old"


def test_get_readings_shape_matches_sqlite(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    table.put_item(Item={
        "id": "stable_id_001",
        "app_id": "test-app",
        "created_at": "2026-06-01T12:00:00Z",
        "entity_type": "water_meter",
        "reading_date": "2026-06-01",
        "meter_name": "main",
        "reading_value": Decimal("123.45"),
        "unit": "m3",
        "notes": "monthly",
    })

    readings = mod.get_readings(None)
    r = readings[0]
    assert set(r.keys()) == {"id", "created_at", "reading_date", "meter_name",
                              "reading_value", "unit", "notes"}
    assert isinstance(r["id"], str)
    assert isinstance(r["reading_value"], (int, float))


def test_get_readings_converts_decimal_back_to_float(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    table.put_item(Item={
        "id": "stable_id_002",
        "app_id": "test-app",
        "created_at": "2026-06-02T12:00:00Z",
        "entity_type": "water_meter",
        "reading_date": "2026-06-02",
        "meter_name": "main",
        "reading_value": Decimal("987.65"),
        "unit": "m3",
        "notes": "",
    })

    readings = mod.get_readings(None)
    assert readings[0]["reading_value"] == 987.65
    assert isinstance(readings[0]["reading_value"], float)


def test_missing_table_raises(monkeypatch):
    monkeypatch.delenv("DYNAMODB_TABLE", raising=False)
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()
    import pytest
    with pytest.raises(ValueError, match="DYNAMODB_TABLE"):
        mod.save_reading(None, 100, "2026-06-01")


def test_default_backend_still_sqlite():
    """Verify the facade still defaults to sqlite when STORAGE_BACKEND is unset."""
    for key in list(sys.modules.keys()):
        if "water_meter.storage" in key:
            del sys.modules[key]
    from app.water_meter import storage as mod
    # sqlite get_db_path should return a file path, not None
    path = mod.get_db_path()
    assert path is not None
    assert path.endswith(".db")


def test_get_meter_names_returns_only_water_meter(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    # Water Meter items with distinct names
    table.put_item(Item={"app_id": "test-app", "created_at": "t1", "entity_type": "water_meter",
                         "meter_name": "garden", "reading_date": "1", "reading_value": 1, "unit": "m3"})
    table.put_item(Item={"app_id": "test-app", "created_at": "t2", "entity_type": "water_meter",
                         "meter_name": "kitchen", "reading_date": "2", "reading_value": 2, "unit": "m3"})
    # Broken Clock item (should be ignored)
    table.put_item(Item={"app_id": "test-app", "created_at": "t3", "entity_type": "broken_clock",
                         "meter_name": "ignored", "real_observed_time": "10:00"})

    names = mod.get_meter_names(None)
    assert names == ["garden", "kitchen"]


def test_get_meter_names_empty_when_no_items(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    names = mod.get_meter_names(None)
    assert names == []


def test_dynamodb_delete_existing_water_meter(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    mod.save_reading(None, 100, "2026-06-01")
    readings = mod.get_readings(None)
    rid = readings[0]["id"]

    result = mod.delete_reading(rid, None)
    assert result is True
    assert len(mod.get_readings(None)) == 0


def test_dynamodb_delete_missing_returns_false(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    result = mod.delete_reading("nonexistent-id", None)
    assert result is False


def test_dynamodb_delete_does_not_delete_broken_clock(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_wm_dynamodb()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    # Water Meter item
    table.put_item(Item={"app_id": "test-app", "created_at": "t1", "entity_type": "water_meter",
                         "id": "wm001", "reading_date": "1", "reading_value": 1, "unit": "m3"})
    # Broken Clock item
    table.put_item(Item={"app_id": "test-app", "created_at": "t2", "entity_type": "broken_clock",
                         "id": "wm001", "real_observed_time": "10:00"})

    # Delete by id that exists in both — should only delete water_meter
    result = mod.delete_reading("wm001", None)
    assert result is True
    remaining = mod.get_readings(None)
    assert len(remaining) == 0  # water_meter deleted
    # Broken Clock item should still exist
    assert len(table.items) == 1
    assert table.items[0]["entity_type"] == "broken_clock"
