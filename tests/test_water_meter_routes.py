"""Tests for Water Meter routes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app as flask_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "test_wm_route.db"
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


def test_form_returns_200(authed_client):
    response = authed_client.get("/water-meter")
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_history_returns_200(authed_client):
    response = authed_client.get("/water-meter/history")
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_valid_html_post_redirects(authed_client):
    response = authed_client.post("/water-meter/readings", data={
        "reading_value": "123.45",
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 302
    assert response.headers["Location"] == "/water-meter/history"


def test_invalid_value_redirects_with_error(authed_client):
    response = authed_client.post("/water-meter/readings", data={
        "reading_value": "-5",
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 302
    assert "?error=" in response.headers["Location"]


def test_invalid_date_redirects_with_error(authed_client):
    response = authed_client.post("/water-meter/readings", data={
        "reading_value": "100",
        "reading_date": "bad-date",
    })
    assert response.status_code == 302
    assert "?error=" in response.headers["Location"]


def test_valid_json_post_returns_201(authed_client):
    response = authed_client.post("/water-meter/readings", json={
        "reading_value": 50,
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True


def test_invalid_json_post_returns_400(authed_client):
    response = authed_client.post("/water-meter/readings", json={
        "reading_value": "not-a-number",
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_history_json_returns_list(authed_client):
    authed_client.post("/water-meter/readings", json={
        "reading_value": 100,
        "reading_date": "2026-06-01",
    })
    response = authed_client.get("/water-meter/history", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["reading_value"] == 100


def test_history_shows_added_reading_after_post(authed_client):
    authed_client.post("/water-meter/readings", data={
        "reading_value": "200",
        "reading_date": "2026-07-01",
        "meter_name": "garden",
    })
    response = authed_client.get("/water-meter/history")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "garden" in text
    assert "200" in text


def test_form_contains_datalist(authed_client):
    """GET /water-meter renders a datalist element."""
    response = authed_client.get("/water-meter")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "<datalist" in text or "meter-name-options" in text


def test_form_contains_meter_name_field(authed_client):
    response = authed_client.get("/water-meter")
    text = response.get_data(as_text=True)
    assert 'name="meter_name"' in text


def test_delete_json_success(authed_client):
    # Create a reading
    authed_client.post("/water-meter/readings", json={"reading_value": 100, "reading_date": "2026-06-01"})
    history = authed_client.get("/water-meter/history", headers={"Accept": "application/json"})
    rid = history.get_json()[0]["id"]

    response = authed_client.delete(f"/water-meter/readings/{rid}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["deleted"] is True
    assert str(data["id"]) == str(rid)


def test_delete_json_not_found(authed_client):
    response = authed_client.delete("/water-meter/readings/9999")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_delete_html_post_redirects(authed_client):
    authed_client.post("/water-meter/readings", data={"reading_value": "100", "reading_date": "2026-06-01"})
    history = authed_client.get("/water-meter/history", headers={"Accept": "application/json"})
    rid = history.get_json()[0]["id"]

    response = authed_client.post(f"/water-meter/readings/{rid}/delete")
    assert response.status_code == 302
    assert response.headers["Location"] == "/water-meter/history"


def test_delete_html_post_not_found(authed_client):
    response = authed_client.post("/water-meter/readings/9999/delete")
    assert response.status_code == 404
    assert "text/html" in response.content_type
