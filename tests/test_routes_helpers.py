"""Focused tests for app/routes.py helper branches.

Covers _parse_request_data(), _notification_class(), and edge cases
in request validation — lines 84, 97, 101, 105, 110, 118-122.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app as flask_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Client with isolated temp DB so writes don't pollute data/app.db."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


# ── Test 1: Empty JSON request body (line 84) ──

def test_empty_json_body_returns_400(client):
    """POST /broken-clock/calculate with empty/None body returns 400."""
    response = client.post(
        "/broken-clock/calculate",
        data="",
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Request must be JSON or form data" in data["error"]


# ── Test 2: Missing real_observed_time defaults to current HH:MM (line 97) ──

def test_missing_real_observed_time_defaults(client):
    """POST with only wrong_observed_time defaults real_observed_time to system time."""
    payload = {
        "wrong_observed_time": "11:00",
        "target_wrong_times": ["07:00"],
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "real_observed_time" in data
    # Should be formatted as HH:MM
    assert len(data["real_observed_time"]) == 5
    assert data["real_observed_time"][2] == ":"


# ── Test 3: String target_wrong_times split (line 101) ──

def test_form_string_target_wrong_times_split(client):
    """Form POST with comma-separated target_wrong_times works."""
    form_data = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "target_wrong_times": "07:00,09:00",
    }
    response = client.post("/broken-clock/calculate", data=form_data)
    assert response.status_code == 200
    assert "text/html" in response.content_type
    text = response.get_data(as_text=True)
    assert "07:00" in text
    assert "09:00" in text


# ── Test 4: Non-string/non-list target_wrong_times fallback (line 105) ──

def test_dict_target_wrong_times_falls_back_to_defaults(client):
    """JSON POST with target_wrong_times as a dict falls back to default refs."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "target_wrong_times": {"bad": "data"},
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    refs = {r["wrong_time"]: r for r in data["reference_points"]}
    assert "00:00" in refs
    assert "07:00" in refs
    assert "09:00" in refs


# ── Test 5: Invalid target time (line 110) ──

def test_invalid_target_time_returns_400(client):
    """POST with invalid target time returns 400 and error message."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "target_wrong_times": ["99:99"],
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Invalid target time: 99:99" in data["error"]


# ── Test 6: _notification_class branches (lines 118-122) ──

from app.routes import _notification_class

def test_notification_class_accurate():
    assert _notification_class("accurate") == "is-success"

def test_notification_class_fast():
    assert _notification_class("fast") == "is-warning"

def test_notification_class_slow():
    assert _notification_class("slow") == "is-danger"
