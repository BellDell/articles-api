"""Test helpers for authorization — login helper for authenticated requests."""

from app.app import app


def login(client, username="testuser", password="secret123"):
    """Register and login a test user. Returns the client."""
    client.post("/auth/register", json={
        "username": username,
        "password": password,
        "confirm_password": password,
    })
    client.post("/auth/login", json={
        "username": username,
        "password": password,
    })
    return client


def login_and_create_bc_record(client, username="testuser", password="secret123"):
    """Login and create a broken clock record, returning the record id."""
    login(client, username, password)
    client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    })
    resp = client.get("/broken-clock/history", headers={"Accept": "application/json"})
    return resp.get_json()[0]["id"]


def login_and_create_wm_record(client, username="testuser", password="secret123"):
    """Login and create a water meter reading, returning the record id."""
    login(client, username, password)
    client.post("/water-meter/readings", json={
        "reading_value": 100,
        "reading_date": "2026-06-01",
    })
    resp = client.get("/water-meter/history", headers={"Accept": "application/json"})
    return resp.get_json()[0]["id"]
