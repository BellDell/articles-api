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


def test_form_returns_200(client):
    response = client.get("/water-meter")
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_history_returns_200(client):
    response = client.get("/water-meter/history")
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_valid_html_post_redirects(client):
    response = client.post("/water-meter/readings", data={
        "reading_value": "123.45",
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 302
    assert response.headers["Location"] == "/water-meter/history"


def test_invalid_value_redirects_with_error(client):
    response = client.post("/water-meter/readings", data={
        "reading_value": "-5",
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 302
    assert "?error=" in response.headers["Location"]


def test_invalid_date_redirects_with_error(client):
    response = client.post("/water-meter/readings", data={
        "reading_value": "100",
        "reading_date": "bad-date",
    })
    assert response.status_code == 302
    assert "?error=" in response.headers["Location"]


def test_valid_json_post_returns_201(client):
    response = client.post("/water-meter/readings", json={
        "reading_value": 50,
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True


def test_invalid_json_post_returns_400(client):
    response = client.post("/water-meter/readings", json={
        "reading_value": "not-a-number",
        "reading_date": "2026-06-01",
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_history_json_returns_list(client):
    client.post("/water-meter/readings", json={
        "reading_value": 100,
        "reading_date": "2026-06-01",
    })
    response = client.get("/water-meter/history", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["reading_value"] == 100


def test_history_shows_added_reading_after_post(client):
    client.post("/water-meter/readings", data={
        "reading_value": "200",
        "reading_date": "2026-07-01",
        "meter_name": "garden",
    })
    response = client.get("/water-meter/history")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "garden" in text
    assert "200" in text
