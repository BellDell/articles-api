"""Tests for the home page at GET /."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_home_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_home_page_returns_html(client):
    response = client.get("/")
    assert "text/html" in response.content_type


def test_home_page_contains_calculator_link(client):
    response = client.get("/")
    text = response.get_data(as_text=True)
    assert "/broken-clock" in text


def test_home_page_contains_history_link(client):
    response = client.get("/")
    text = response.get_data(as_text=True)
    assert "/broken-clock/history" in text


def test_existing_pages_still_work(client):
    response = client.get("/broken-clock")
    assert response.status_code == 200
    assert "text/html" in response.content_type
