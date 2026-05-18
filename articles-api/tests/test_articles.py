import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import app

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    assert "author" in author
    assert "id" in author["author"]
    assert "first_name" in author["author"]
    assert "last_name" in author["author"]

# def test_get_articles_returns_articles_with_authors(client):
#     response = client.get("/articles")
#     assert response.status_code == 200
#     data = response.get_json()
#     assert isinstance(data, list)
#     assert len(data) > 0
#
#     article = data[0]
#
#     assert "author" in article
#     assert "id" in article["author"]
#     assert "title" in article["author"]
#     assert "content" in article["author"]
#     assert "first_name" in article["author"]
#     assert "last_name" in article["author"]


def test_get_article_by_id_returns_article_with_author(client):
    response = client.get("/articles/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == 1
    assert "title" in data
    assert "content" in data
    assert "author" in data
#
#
# def test_get_article_by_unknown_id_returns_404(client):
#     response = client.get("/articles/999")
#     assert response.status_code == 404