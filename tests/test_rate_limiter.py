"""Tests for the write rate limiter (SQLite + routes)."""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app as flask_app

from app.core.rate_limit.limiter import (
    ip_hash,
    current_window_start,
    retry_after_seconds,
    WINDOW_SECONDS,
    MAX_WRITES,
)
from app.core.rate_limit import storage_sqlite as sqlite_mod


# ── Unit tests: helpers ──

def test_ip_hash_returns_hex_string():
    h = ip_hash("127.0.0.1")
    assert isinstance(h, str)
    assert len(h) == 16


def test_ip_hash_same_ip_same_hash():
    assert ip_hash("192.168.1.1") == ip_hash("192.168.1.1")


def test_ip_hash_different_ip_different_hash():
    assert ip_hash("192.168.1.1") != ip_hash("10.0.0.1")


def test_current_window_start_aligned():
    ts = 0
    start = current_window_start(ts)
    assert start == 0


def test_current_window_start_mid_window():
    ts = 21600
    start = current_window_start(ts)
    assert start == 0


def test_current_window_start_next_window():
    ts = 43200
    start = current_window_start(ts)
    assert start == 43200


def test_retry_after_seconds_positive():
    now = int(time.time())
    secs = retry_after_seconds(now)
    assert secs > 0
    assert secs <= WINDOW_SECONDS


# ── SQLite rate limiter tests ──

def test_sqlite_allows_first_five_writes(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_rl1.db")
    monkeypatch.setenv("APP_DB_PATH", db_path)
    for i in range(5):
        allowed, retry = sqlite_mod.consume_write_quota("broken_clock", "10.0.0.1")
        assert allowed, f"Write {i+1} should be allowed"
        assert retry == 0


def test_sqlite_blocks_sixth_write(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_rl2.db")
    monkeypatch.setenv("APP_DB_PATH", db_path)
    for _ in range(5):
        sqlite_mod.consume_write_quota("broken_clock", "10.0.0.1")
    allowed, retry = sqlite_mod.consume_write_quota("broken_clock", "10.0.0.1")
    assert not allowed
    assert isinstance(retry, int)
    assert retry > 0


def test_sqlite_separate_feature_quotas(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_rl3.db")
    monkeypatch.setenv("APP_DB_PATH", db_path)
    for _ in range(5):
        sqlite_mod.consume_write_quota("broken_clock", "10.0.0.1")
    allowed, _ = sqlite_mod.consume_write_quota("water_meter", "10.0.0.1")
    assert allowed


def test_sqlite_separate_ip_quotas(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_rl4.db")
    monkeypatch.setenv("APP_DB_PATH", db_path)
    for _ in range(5):
        sqlite_mod.consume_write_quota("broken_clock", "10.0.0.1")
    allowed, _ = sqlite_mod.consume_write_quota("broken_clock", "10.0.0.2")
    assert allowed


# ── DynamoDB rate limiter tests ──

def _make_mock_table(items=None):
    if items is None:
        items = []

    class MockExceptions:
        ConditionalCheckFailedException = Exception

    class MockClient:
        exceptions = MockExceptions()

    class MockMeta:
        client = MockClient()

    class MockTable:
        def __init__(self, items):
            self.items = items
            self.meta = MockMeta()

        def update_item(self, Key, **kwargs):
            app_id = Key["app_id"]
            bucket = Key["created_at"]
            max_val = kwargs.get("ExpressionAttributeValues", {}).get(":max", 5)
            for item in self.items:
                if item.get("app_id") == app_id and item.get("created_at") == bucket:
                    current = item.get("counter", 0)
                    if current >= max_val:
                        raise self.meta.client.exceptions.ConditionalCheckFailedException(
                            {"Error": {"Code": "ConditionalCheckFailedException"}},
                            "UpdateItem",
                        )
                    item["counter"] = current + 1
                    return {"Attributes": {"counter": item["counter"]}}
            new_item = {
                "app_id": app_id,
                "created_at": bucket,
                "counter": 1,
                "entity_type": "rate_limit",
            }
            self.items.append(new_item)
            return {"Attributes": {"counter": 1}}

    return MockTable(items)


def test_dynamodb_allows_first_five_writes(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-rate-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mock_table = _make_mock_table()
    monkeypatch.setattr("app.core.rate_limit.storage_dynamodb.get_dynamodb_table",
                        lambda: mock_table)
    from app.core.rate_limit import storage_dynamodb as mod

    for i in range(5):
        allowed, retry = mod.consume_write_quota("broken_clock", "10.0.0.1")
        assert allowed, f"Write {i+1} should be allowed"
        assert retry == 0


def test_dynamodb_blocks_sixth_write(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-rate-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mock_table = _make_mock_table()
    monkeypatch.setattr("app.core.rate_limit.storage_dynamodb.get_dynamodb_table",
                        lambda: mock_table)
    from app.core.rate_limit import storage_dynamodb as mod

    for _ in range(5):
        mod.consume_write_quota("broken_clock", "10.0.0.1")
    allowed, retry = mod.consume_write_quota("broken_clock", "10.0.0.1")
    assert not allowed
    assert isinstance(retry, int)
    assert retry > 0


def test_dynamodb_uses_deterministic_key(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-rate-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mock_table = _make_mock_table()
    monkeypatch.setattr("app.core.rate_limit.storage_dynamodb.get_dynamodb_table",
                        lambda: mock_table)
    from app.core.rate_limit import storage_dynamodb as mod

    mod.consume_write_quota("broken_clock", "10.0.0.1")
    assert len(mock_table.items) == 1
    item = mock_table.items[0]
    assert item["created_at"].startswith("rate_limit#")
    assert item["entity_type"] == "rate_limit"


def test_dynamodb_separate_feature_quotas(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-rate-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mock_table = _make_mock_table()
    monkeypatch.setattr("app.core.rate_limit.storage_dynamodb.get_dynamodb_table",
                        lambda: mock_table)
    from app.core.rate_limit import storage_dynamodb as mod

    for _ in range(5):
        mod.consume_write_quota("broken_clock", "10.0.0.1")
    allowed, _ = mod.consume_write_quota("water_meter", "10.0.0.1")
    assert allowed


def test_dynamodb_separate_ip_quotas(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-rate-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mock_table = _make_mock_table()
    monkeypatch.setattr("app.core.rate_limit.storage_dynamodb.get_dynamodb_table",
                        lambda: mock_table)
    from app.core.rate_limit import storage_dynamodb as mod

    for _ in range(5):
        mod.consume_write_quota("broken_clock", "10.0.0.1")
    allowed, _ = mod.consume_write_quota("broken_clock", "10.0.0.2")
    assert allowed


def test_dynamodb_stores_hashed_ip_not_raw(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-rate-table")
    monkeypatch.setenv("APP_ID", "test-app")
    mock_table = _make_mock_table()
    monkeypatch.setattr("app.core.rate_limit.storage_dynamodb.get_dynamodb_table",
                        lambda: mock_table)
    from app.core.rate_limit import storage_dynamodb as mod

    mod.consume_write_quota("broken_clock", "192.168.1.1")
    assert "192.168.1.1" not in mock_table.items[0]["created_at"]
    assert "#" in mock_table.items[0]["created_at"]


# ── Route tests: 429 behavior ──

@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "test_429.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_broken_clock_sixth_write_returns_429(client):
    for _ in range(5):
        resp = client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        assert resp.status_code == 200
    resp = client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    })
    assert resp.status_code == 429
    assert resp.get_json() == {"error": "Rate limit exceeded. Try again later."}
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) >= 0


def test_broken_clock_invalid_does_not_consume_quota(client):
    for _ in range(5):
        client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
    resp = client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "",
        "real_observed_time": "10:00",
    })
    assert resp.status_code == 400
    resp = client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "12:00",
        "real_observed_time": "11:00",
    })
    assert resp.status_code == 429


def test_broken_clock_and_water_meter_separate_quotas(client):
    for _ in range(5):
        client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
    resp = client.post("/water-meter/readings", json={
        "reading_value": 100,
        "reading_date": "2026-06-01",
    })
    assert resp.status_code == 201


def test_water_meter_sixth_write_returns_429(client):
    for _ in range(5):
        resp = client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
        assert resp.status_code == 201
    resp = client.post("/water-meter/readings", json={
        "reading_value": 100,
        "reading_date": "2026-06-01",
    })
    assert resp.status_code == 429
    assert resp.get_json() == {"error": "Rate limit exceeded. Try again later."}
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) >= 0


def test_water_meter_invalid_does_not_consume_quota(client):
    for _ in range(5):
        client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
    resp = client.post("/water-meter/readings", json={
        "reading_value": -5,
        "reading_date": "2026-06-01",
    })
    assert resp.status_code == 400
    resp = client.post("/water-meter/readings", json={
        "reading_value": 200,
        "reading_date": "2026-06-01",
    })
    assert resp.status_code == 429
