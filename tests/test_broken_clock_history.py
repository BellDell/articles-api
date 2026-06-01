"""Tests for Broken Clock SQLite history persistence."""

import json
import os
import pytest
from app.app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Set up a client with an isolated temporary database."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_successful_calculation_creates_history_record(client):
    """A successful JSON calculation creates exactly one history row."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200

    history = client.get("/broken-clock/history")
    assert history.status_code == 200
    data = history.get_json()
    assert len(data) == 1
    assert data[0]["offset_minutes"] == 60


def test_invalid_calculation_does_not_create_record(client):
    """A validation error (400) must not create a history row."""
    payload = {
        "real_observed_time": "10:00",
        # missing wrong_observed_time
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 400

    history = client.get("/broken-clock/history")
    assert history.status_code == 200
    data = history.get_json()
    assert len(data) == 0


def test_history_newest_first(client):
    """Multiple calculations are returned newest first."""
    client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "10:00",
        "real_observed_time": "09:00",
    })
    client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    })

    history = client.get("/broken-clock/history")
    data = history.get_json()
    assert len(data) == 2
    # Second request (offset 60) should be first (newest)
    assert data[0]["offset_minutes"] == 60
    assert data[1]["offset_minutes"] == 60


def test_history_decodes_json_fields(client):
    """History response decodes target_wrong_times and reference_points as arrays."""
    payload = {
        "wrong_observed_time": "13:00",
        "real_observed_time": "12:00",
        "target_wrong_times": ["12:00"],
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200

    history = client.get("/broken-clock/history")
    data = history.get_json()
    assert len(data) == 1
    record = data[0]
    assert isinstance(record["target_wrong_times"], list)
    assert isinstance(record["reference_points"], list)
    assert record["target_wrong_times"] == ["12:00"]
    assert len(record["reference_points"]) == 1
    assert record["reference_points"][0]["wrong_time"] == "12:00"
