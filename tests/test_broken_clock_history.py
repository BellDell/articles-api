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


# ---------------------------------------------------------------------------
# calc_date route/storage tests
# ---------------------------------------------------------------------------

def test_calc_date_defaults_to_today_when_missing(authed_client):
    """POST with no calc_date stores and returns today's date."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    }
    response = authed_client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "calc_date" in data
    from datetime import date
    assert data["calc_date"] == date.today().isoformat()


def test_calc_date_stores_provided_date(authed_client):
    """POST with a valid calc_date stores and returns that date."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "calc_date": "2026-01-15",
    }
    response = authed_client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["calc_date"] == "2026-01-15"


def test_calc_date_invalid_falls_back_to_today(authed_client):
    """POST with invalid calc_date falls back to today."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "calc_date": "not-a-date",
    }
    response = authed_client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    from datetime import date
    assert data["calc_date"] == date.today().isoformat()


def test_calc_date_in_json_history(authed_client):
    """History JSON response includes calc_date for stored records."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "calc_date": "2026-03-20",
    }
    authed_client.post("/broken-clock/calculate", json=payload)

    history = authed_client.get("/broken-clock/history", headers={"Accept": "application/json"})
    assert history.status_code == 200
    data = history.get_json()
    assert len(data) >= 1
    assert data[0]["calc_date"] == "2026-03-20"


def test_calc_date_in_html_history(authed_client):
    """History HTML page shows Date column with values."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "calc_date": "2026-07-04",
    }
    authed_client.post("/broken-clock/calculate", json=payload)

    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "2026-07-04" in text
    assert "Date" in text  # Column header


def test_calc_date_result_page_shows_date(authed_client, monkeypatch):
    """Result page displays 'Results — YYYY-MM-DD'."""
    # Use form POST for server-rendered result page
    authed_client.post("/auth/register", json={
        "username": "result_user",
        "password": "secret123",
        "confirm_password": "secret123",
    })
    authed_client.post("/auth/login", json={
        "username": "result_user",
        "password": "secret123",
    })
    response = authed_client.post("/broken-clock/calculate", data={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "calc_date": "2026-05-10",
    })
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Results — 2026-05-10" in text


# ---------------------------------------------------------------------------
# SQLite migration idempotency and legacy tests
# ---------------------------------------------------------------------------

def test_sqlite_migration_adds_calc_date(tmp_path):
    """ensure_db_initialized adds calc_date TEXT column idempotently."""
    import app.broken_clock.storage_sqlite as sql
    from contextlib import closing
    db_path = str(tmp_path / "test_migrate_calc.db")
    sql.ensure_db_initialized(db_path)
    with closing(sql.sqlite3.connect(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(broken_clock_history)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "calc_date" in columns


def test_sqlite_migration_calc_date_idempotent(tmp_path):
    """Calling ensure_db_initialized twice does not error on calc_date."""
    import app.broken_clock.storage_sqlite as sql
    db_path = str(tmp_path / "test_migrate_calc2.db")
    sql.ensure_db_initialized(db_path)
    sql.ensure_db_initialized(db_path)  # second call


def test_legacy_record_without_calc_date_uses_created_at(tmp_path):
    """Legacy records with NULL calc_date use created_at date as fallback."""
    import app.broken_clock.storage_sqlite as sql
    import json
    from contextlib import closing
    from datetime import datetime, timezone
    db_path = str(tmp_path / "test_legacy_calc.db")
    sql.ensure_db_initialized(db_path)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Insert without calc_date (simulate legacy write)
    with closing(sql.sqlite3.connect(db_path)) as conn:
        conn.execute(
            """INSERT INTO broken_clock_history
               (created_at, real_observed_time, wrong_observed_time,
                offset_minutes, offset_human, clock_status,
                target_wrong_times_json, reference_points_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (created, "10:00", "11:00", 60, "+60", "fast",
             json.dumps([]), json.dumps([])),
        )
        conn.commit()
    # Now run get_history and check fallback
    records = sql.get_history(db_path)
    assert len(records) == 1
    assert records[0]["calc_date"] == created[:10]


# ---------------------------------------------------------------------------
# Frontend sort tests
# ---------------------------------------------------------------------------

def test_history_table_has_id(authed_client):
    """History table has id="broken-clock-history-table"."""
    authed_client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    })
    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    text = response.get_data(as_text=True)
    assert 'id="broken-clock-history-table"' in text


def test_history_date_header_has_marker(authed_client):
    """Date header shows descending indicator."""
    authed_client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
    })
    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    text = response.get_data(as_text=True)
    assert "▼" in text


def test_history_shows_calc_date_values(authed_client):
    """History HTML contains calc_date values in the Date column."""
    authed_client.post("/broken-clock/calculate", json={
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        "calc_date": "2026-03-15",
    })
    response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
    text = response.get_data(as_text=True)
    assert "2026-03-15" in text
    assert "Date" in text
