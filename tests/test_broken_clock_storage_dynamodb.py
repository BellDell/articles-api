"""Tests for DynamoDB Broken Clock history storage backend."""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeTable:
    """A minimal fake DynamoDB table for testing."""

    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)

    def query(self, KeyConditionExpression, ExpressionAttributeValues,
              ScanIndexForward, ExclusiveStartKey=None):
        # Filter by app_id
        expected_aid = ExpressionAttributeValues.get(":aid")
        matching = [it for it in self.items if it.get("app_id") == expected_aid]
        # Sort by created_at descending for ScanIndexForward=False
        matching.sort(key=lambda it: it.get("created_at", ""), reverse=True)
        return {"Items": matching}


class FakeDynamoDB:
    def __init__(self):
        self._tables = {}

    def Table(self, name):
        if name not in self._tables:
            self._tables[name] = FakeTable()
        return self._tables[name]


def _reload_dynamodb_storage():
    """Remove cached dynamodb modules so next import picks up fresh env vars."""
    for key in list(sys.modules.keys()):
        if "broken_clock.storage_dynamodb" in key:
            del sys.modules[key]
    import app.broken_clock.storage_dynamodb as mod
    return mod


def test_dynamodb_dispatches_correctly(monkeypatch):
    """STORAGE_BACKEND=dynamodb dispatches to dynamodb backend."""
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    if "app.broken_clock.storage" in sys.modules:
        del sys.modules["app.broken_clock.storage"]
    import app.broken_clock.storage as mod
    # get_db_path should return None for dynamodb (no file path)
    assert mod.get_db_path() is None


def test_dynamodb_missing_table_raises(monkeypatch):
    """Missing DYNAMODB_TABLE raises ValueError when a storage function is called."""
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.delenv("DYNAMODB_TABLE", raising=False)
    if "app.broken_clock.storage" in sys.modules:
        del sys.modules["app.broken_clock.storage"]
    import app.broken_clock.storage as mod
    import pytest
    with pytest.raises(ValueError, match="DYNAMODB_TABLE"):
        mod.save_calculation(
            None, "10:00", "11:00", 60, "+60 minutes", "fast",
            ["07:00"], [{"wrong_time": "07:00", "real_time": "06:00", "day_shift": 0}],
        )


def test_dynamodb_save_calculation_writes_item(monkeypatch):
    """save_calculation writes the expected item shape."""
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_dynamodb_storage()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    mod.save_calculation(
        None, "10:00", "11:00", 60, "+60 minutes", "fast",
        ["07:00"], [{"wrong_time": "07:00", "real_time": "06:00", "day_shift": 0}],
    )

    table = fake_db.Table("test-table")
    assert len(table.items) == 1
    item = table.items[0]
    assert item["app_id"] == "test-app"
    assert item["real_observed_time"] == "10:00"
    assert item["offset_minutes"] == 60
    assert json.loads(item["target_wrong_times"]) == ["07:00"]
    assert json.loads(item["reference_points"])[0]["wrong_time"] == "07:00"


def test_dynamodb_get_history_returns_correct_shape(monkeypatch):
    """get_history returns SQLite-compatible shape with decoded JSON fields."""
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_dynamodb_storage()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    table.put_item(Item={
        "app_id": "test-app",
        "created_at": "2026-01-01T12:00:00Z",
        "real_observed_time": "10:00",
        "wrong_observed_time": "11:00",
        "offset_minutes": 60,
        "offset_human": "+60 minutes",
        "clock_status": "fast",
        "target_wrong_times": json.dumps(["07:00"]),
        "reference_points": json.dumps([{"wrong_time": "07:00", "real_time": "06:00", "day_shift": 0}]),
    })

    history = mod.get_history(None)
    assert len(history) == 1
    record = history[0]
    assert record["id"] == 1
    assert record["real_observed_time"] == "10:00"
    assert record["offset_minutes"] == 60
    assert isinstance(record["target_wrong_times"], list)
    assert isinstance(record["reference_points"], list)
    assert record["target_wrong_times"] == ["07:00"]


def test_dynamodb_get_history_newest_first(monkeypatch):
    """get_history returns records newest first."""
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mod = _reload_dynamodb_storage()

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)

    table = fake_db.Table("test-table")
    table.put_item(Item={
        "app_id": "test-app",
        "created_at": "2026-01-01T10:00:00Z",
        "real_observed_time": "09:00",
        "wrong_observed_time": "10:00",
        "offset_minutes": 60,
        "offset_human": "+60 minutes",
        "clock_status": "fast",
        "target_wrong_times": json.dumps([]),
        "reference_points": json.dumps([]),
    })
    table.put_item(Item={
        "app_id": "test-app",
        "created_at": "2026-01-02T10:00:00Z",
        "real_observed_time": "10:00",
        "wrong_observed_time": "11:00",
        "offset_minutes": 60,
        "offset_human": "+60 minutes",
        "clock_status": "fast",
        "target_wrong_times": json.dumps([]),
        "reference_points": json.dumps([]),
    })

    history = mod.get_history(None)
    assert len(history) == 2
    # Newest first
    assert history[0]["created_at"] > history[1]["created_at"]


def test_dynamodb_ensure_db_initialized_is_noop(monkeypatch):
    """ensure_db_initialized does nothing and does not raise."""
    mod = _reload_dynamodb_storage()
    # Should not raise any exception
    mod.ensure_db_initialized(None)
