"""Tests for delete history record functionality (SQLite + DynamoDB + routes)."""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# ── SQLite storage tests ──


def _make_sqlite_storage(tmp_path):
    """Return a (storage_module, db_path) tuple with a clean temp DB."""
    from app.broken_clock import storage_sqlite as mod
    db_path = str(tmp_path / "test_delete.db")
    # Ensure table exists
    mod.ensure_db_initialized(db_path)
    return mod, db_path


def test_sqlite_delete_existing_record_returns_true(tmp_path):
    mod, db_path = _make_sqlite_storage(tmp_path)
    # Insert a record
    mod.save_calculation(db_path, "10:00", "11:00", 60, "+60 minutes", "fast",
                         ["07:00"], [{"wrong_time": "07:00", "real_time": "06:00", "day_shift": 0}])
    records = mod.get_history(db_path)
    assert len(records) == 1
    record_id = records[0]["id"]

    result = mod.delete_history_record(record_id, db_path)
    assert result is True

    remaining = mod.get_history(db_path)
    assert len(remaining) == 0


def test_sqlite_delete_missing_record_returns_false(tmp_path):
    mod, db_path = _make_sqlite_storage(tmp_path)
    result = mod.delete_history_record(9999, db_path)
    assert result is False


# ── DynamoDB storage tests ──

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
                      if not (it["app_id"] == Key["app_id"]
                              and it["created_at"] == Key["created_at"])]


class FakeDynamoDB:
    def __init__(self):
        self._tables = {}

    def Table(self, name):
        if name not in self._tables:
            self._tables[name] = FakeTable()
        return self._tables[name]


def _make_dynamodb_mod(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")
    for key in list(sys.modules.keys()):
        if "broken_clock.storage_dynamodb" in key:
            del sys.modules[key]
    import app.broken_clock.storage_dynamodb as mod

    fake_db = FakeDynamoDB()
    monkeypatch.setattr("boto3.resource", lambda service, **kw: fake_db)
    return mod, fake_db


def test_dynamodb_delete_existing_record_returns_true(monkeypatch):
    mod, fake_db = _make_dynamodb_mod(monkeypatch)

    # Save via mod.save_calculation (generates stable id)
    mod.save_calculation(
        None, "10:00", "11:00", 60, "+60 minutes", "fast",
        ["07:00"], [{"wrong_time": "07:00", "real_time": "06:00", "day_shift": 0}],
    )

    records = mod.get_history(None)
    assert len(records) == 1
    record_id = records[0]["id"]
    assert isinstance(record_id, str)

    result = mod.delete_history_record(record_id, None)
    assert result is True
    assert len(fake_db.Table("test-table").items) == 0


def test_dynamodb_delete_missing_record_returns_false(monkeypatch):
    mod, _ = _make_dynamodb_mod(monkeypatch)
    result = mod.delete_history_record(9999, None)
    assert result is False


# ── Route tests ──

from app.app import app as flask_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    """SQLite client with isolated temp DB."""
    db_path = tmp_path / "test_delete_route.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(client):
    """Client with registered and logged-in user."""
    client.post("/auth/register", json={
        "username": "testuser",
        "password": "secret123",
        "confirm_password": "secret123",
    })
    client.post("/auth/login", json={
        "username": "testuser",
        "password": "secret123",
    })
    return client


def _create_one_record(client):
    """Helper: POST a valid calculation and return its id."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    }
    client.post("/broken-clock/calculate", json=payload)
    resp = client.get("/broken-clock/history", headers={"Accept": "application/json"})
    data = resp.get_json()
    return data[0]["id"]


def test_delete_json_success(authed_client):
    rid = _create_one_record(authed_client)

    response = authed_client.delete(f"/broken-clock/history/{rid}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["deleted"] is True
    # SQLite returns int id, route returns string from URL param
    assert str(data["id"]) == str(rid)


def test_delete_json_not_found(authed_client):
    response = authed_client.delete("/broken-clock/history/9999")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    # Route returns string id from URL param
    assert data["id"] == "9999"


def test_delete_html_post_redirects(authed_client):
    rid = _create_one_record(authed_client)

    response = authed_client.post(f"/broken-clock/history/{rid}/delete")
    assert response.status_code == 302
    assert response.headers["Location"] == "/broken-clock/history"


def test_delete_html_post_not_found(authed_client):
    response = authed_client.post("/broken-clock/history/9999/delete")
    assert response.status_code == 404
    assert "text/html" in response.content_type
