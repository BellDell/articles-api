from app.app import app
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


# New tests for POST /articles

def test_create_article_success(client):
    payload = {
        "title": "New Article",
        "content": "Interesting content",
        "author_id": 1,
    }
    response = client.post("/articles", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["content"] == payload["content"]
    assert "author" in data
    # author object should not include author_id in article response
    assert "author_id" not in data


def test_create_article_missing_field_returns_400(client):
    payload = {
        "title": "Incomplete",
    }
    response = client.post("/articles", json=payload)
    assert response.status_code == 400


def test_create_article_unknown_author_returns_400(client):
    payload = {
        "title": "Orphan",
        "content": "No parent",
        "author_id": 999,
    }
    response = client.post("/articles", json=payload)
    assert response.status_code == 400
