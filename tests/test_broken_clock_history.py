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


def _login(client):
    client.post("/auth/register", json={
        "username": "testuser",
        "password": "secret123",
        "confirm_password": "secret123",
    })
    client.post("/auth/login", json={
        "username": "testuser",
        "password": "secret123",
    })


def test_successful_calculation_creates_history_record(authed_client):
    """A successful JSON calculation creates exactly one history row."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    }
    response = authed_client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200

    history = authed_client.get("/broken-clock/history", headers={"Accept": "application/json"})
    assert history.status_code == 200
    data = history.get_json()
    assert len(data) == 1
    assert data[0]["offset_minutes"] == 60


def test_invalid_calculation_does_not_create_record(authed_client):
    """A validation error (400) must not create a history row."""
    payload = {
        "real_observed_time": "10:00",
        # missing wrong_observed_time
    }
    response = authed_client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 400

    history = authed_client.get("/broken-clock/history", headers={"Accept": "application/json"})
    assert history.status_code == 200
    data = history.get_json()
    assert len(data) == 0


def test_history_newest_first(authed_client):
    """Multiple calculations are returned newest first."""
    authed_client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "10:00",
        "real_observed_time": "09:00",
    })
    authed_client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    })

    history = authed_client.get("/broken-clock/history", headers={"Accept": "application/json"})
    data = history.get_json()
    assert len(data) == 2
    # Second request (offset 60) should be first (newest)
    assert data[0]["offset_minutes"] == 60
    assert data[1]["offset_minutes"] == 60


def test_history_decodes_json_fields(authed_client):
    """History response decodes target_wrong_times and reference_points as arrays."""
    payload = {
        "wrong_observed_time": "13:00",
        "real_observed_time": "12:00",
        "target_wrong_times": ["12:00"],
    }
    response = authed_client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200

    history = authed_client.get("/broken-clock/history", headers={"Accept": "application/json"})
    data = history.get_json()
    assert len(data) == 1
    record = data[0]
    assert isinstance(record["target_wrong_times"], list)
    assert isinstance(record["reference_points"], list)
    assert record["target_wrong_times"] == ["12:00"]
    assert len(record["reference_points"]) == 1
    assert record["reference_points"][0]["wrong_time"] == "12:00"


# HTML browser tests

def test_history_html_returns_html(authed_client):
    """GET /broken-clock/history with Accept text/html returns 200 and text/html."""
    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_history_html_empty_shows_no_calculations(authed_client):
    """Empty history HTML page contains 'No calculations yet'."""
    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "No calculations yet" in response.get_data(as_text=True)


def test_history_html_with_record_shows_reference_points(authed_client):
    """History HTML page with one saved calculation shows compact reference point."""
    payload = {
        "wrong_observed_time": "07:00",
        "real_observed_time": "06:00",
        "target_wrong_times": ["07:00"],
    }
    authed_client.post("/broken-clock/calculate", json=payload)

    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Calculation History" in text
    assert "07:00" in text
