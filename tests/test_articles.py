import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app




@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_get_authors_returns_authors(client):
    response = client.get("/authors")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0

    author = data[0]
    assert "id" in author
    assert "first_name" in author
    assert "last_name" in author


def test_get_articles_returns_articles_with_authors(client):
    response = client.get("/articles")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0

    article = data[0]

    assert "author" in article
    assert "id" in article
    assert "title" in article
    assert "content" in article
    assert "id" in article["author"]
    assert "first_name" in article["author"]
    assert "last_name" in article["author"]


def test_get_article_by_id_returns_article_with_author(client):
    response = client.get("/articles/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == 1
    assert "title" in data
    assert "content" in data
    assert "author" in data


def test_get_article_by_unknown_id_returns_404(client):
    response = client.get("/articles/999")
    assert response.status_code == 404


def test_get_author_by_id_returns_author(client):
    response = client.get("/author/1")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "id" in data
    assert "first_name" in data
    assert "last_name" in data
    assert data["id"] == 1


def test_get_author_by_unknown_id_returns_404(client):
    response = client.get("/author/999")
    assert response.status_code == 404
    data = response.get_json()
    assert isinstance(data, dict)
    assert "error" in data


def test_broken_clock_form_returns_200(client):
    """GET /broken-clock returns 200 with HTML form."""
    response = client.get("/broken-clock")
    assert response.status_code == 200
    assert "Broken Clock Calculator" in response.text


def test_broken_clock_fast_clock_default_refs(client):
    """Fast clock with default reference points."""
    payload = {
        "wrong_observed_time": "11:00",
        "real_observed_time": "10:00",
        # no target_wrong_times provided
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["offset_minutes"] == 60
    assert data["offset_human"] == "+60 minutes"
    assert data["clock_status"] == "fast"
    refs = {r["wrong_time"]: r for r in data["reference_points"]}
    assert refs["00:00"]["real_time"] == "23:00"
    assert refs["00:00"]["day_shift"] == -1
    assert refs["07:00"]["real_time"] == "06:00"
    assert refs["07:00"]["day_shift"] == 0
    assert refs["09:00"]["real_time"] == "08:00"
    assert refs["09:00"]["day_shift"] == 0


def test_broken_clock_slow_clock_scenario(client):
    """Slow clock mapping checks."""
    payload = {
        "wrong_observed_time": "09:15",
        "real_observed_time": "10:00",
        "target_wrong_times": ["07:00", "09:00"]
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["offset_minutes"] == -45
    refs = {r["wrong_time"]: r for r in data["reference_points"]}
    assert refs["07:00"]["real_time"] == "07:45"
    assert refs["09:00"]["real_time"] == "09:45"


def test_broken_clock_missing_wrong_observed_time_400(client):
    """POST /broken-clock/calculate with missing wrong_observed_time returns 400."""
    payload = {
        "real_observed_time": "12:00",
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_broken_clock_invalid_time_format_400(client):
    """POST /broken-clock/calculate with invalid HH:MM returns 400."""
    payload = {
        "wrong_observed_time": "25:00",
        "real_observed_time": "12:00",
        "target_wrong_times": ["15:00"]
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_broken_clock_custom_target_wrong_times(client):
    """POST /broken-clock/calculate with custom target_wrong_times list e.g. ['12:00']."""
    payload = {
        "wrong_observed_time": "13:00",
        "real_observed_time": "12:00",
        "target_wrong_times": ["12:00"]
    }
    response = client.post("/broken-clock/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["offset_minutes"] == 60
    rp = data["reference_points"]
    assert len(rp) == 1
    assert rp[0]["wrong_time"] == "12:00"
    assert rp[0]["real_time"] == "11:00"
    assert rp[0]["day_shift"] == 0
