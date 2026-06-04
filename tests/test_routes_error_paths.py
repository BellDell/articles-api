"""Tests for error/corner-case paths in routes.

These tests patch internal route helpers to force error branches
that are hard to reach through normal request flows.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app as flask_app

# Module-level reference to the routes module for monkeypatching
import app.routes


@pytest.fixture
def client(tmp_path):
    flask_app.config["TESTING"] = True
    os.environ["APP_DB_PATH"] = str(tmp_path / "test_err.db")
    with flask_app.test_client() as client:
        yield client


# ── POST /articles error paths ──

def test_create_article_non_integer_author_id_returns_400(client):
    payload = {
        "title": "Bad",
        "content": "Body",
        "author_id": "not-a-number",
    }
    response = client.post("/articles", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "author_id must be an integer" in data["error"]


# ── Broken Clock calculate DB error paths ──

def test_calculate_db_error_returns_json_500(monkeypatch, client):
    def _raise(*args, **kwargs):
        raise RuntimeError("Disk full")

    monkeypatch.setattr(app.routes, "save_calculation", _raise)

    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_calculate_db_error_returns_html_500(monkeypatch, client):
    def _raise(*args, **kwargs):
        raise RuntimeError("Disk full")

    monkeypatch.setattr(app.routes, "save_calculation", _raise)

    form_data = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    }
    response = client.post("/broken-clock/calculate", data=form_data)
    assert response.status_code == 500
    assert "text/html" in response.content_type
    text = response.get_data(as_text=True)
    assert "Error" in text
    assert "/broken-clock" in text
    assert "Calculate again" in text


# ── Broken Clock history DB error paths ──

def test_history_db_error_returns_json_500(monkeypatch, client):
    def _raise(*args, **kwargs):
        raise RuntimeError("DB failure")

    monkeypatch.setattr(app.routes, "get_history", _raise)

    response = client.get("/broken-clock/history", headers={"Accept": "application/json"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_history_db_error_returns_html_500(monkeypatch, client):
    def _raise(*args, **kwargs):
        raise RuntimeError("DB failure")

    monkeypatch.setattr(app.routes, "get_history", _raise)

    response = client.get("/broken-clock/history", headers={"Accept": "text/html"})
    assert response.status_code == 500
    assert "text/html" in response.content_type
    text = response.get_data(as_text=True)
    assert "Error" in text


def test_water_meter_save_error_returns_html_with_water_meter_back_link(monkeypatch, client):
    def _raise(*args, **kwargs):
        raise RuntimeError("DB failure")

    monkeypatch.setattr(app.routes.wm_storage, "save_reading", _raise)

    response = client.post("/water-meter/readings", data={
        "reading_value": "123.45",
        "reading_date": "2026-06-01",
    })

    assert response.status_code == 500
    assert "text/html" in response.content_type
    text = response.get_data(as_text=True)
    assert "/water-meter" in text
    assert "Add reading" in text
    assert "Calculate again" not in text


def test_water_meter_history_error_returns_html_with_water_meter_back_link(monkeypatch, client):
    def _raise(*args, **kwargs):
        raise RuntimeError("DB failure")

    monkeypatch.setattr(app.routes.wm_storage, "get_readings", _raise)

    response = client.get("/water-meter/history", headers={"Accept": "text/html"})

    assert response.status_code == 500
    assert "text/html" in response.content_type
    text = response.get_data(as_text=True)
    assert "/water-meter" in text
    assert "Add reading" in text
    assert "Calculate again" not in text
