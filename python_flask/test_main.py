from main import *

import json
import pytest


@pytest.fixture(scope="function")
def session(request):
    """Creates a new database session for a test."""
    with app.app_context():
        db.create_all()

    def teardown():
        with app.app_context():
            db.drop_all()

    request.addfinalizer(teardown)
    return db.session


@pytest.fixture
def client():
    return app.test_client()


def test_articles(session, client):
    jane = Author(firstname="Jane", lastname="Doe")
    brief = Article(title="A brief history", author=jane)
    with app.app_context():
        session.add(brief)
        session.commit()
    response = client.get("/articles.json")
    assert json.loads(response.data) == [
        {"author": {"firstname": "Jane", "lastname": "Doe"}, "title": "A brief history"}
    ]


# Uncomment the following line to skip this test
@pytest.mark.skip()
def test_article_by_id(session, client):
    jane = Author(firstname="Jane", lastname="Doe")
    brief = Article(title="A brief history", author=jane)
    with app.app_context():
        session.add(brief)
        session.commit()
    response = client.get("/article.json?id=%i" % (brief.id))
    assert json.loads(response.data) == {
        "author": {"firstname": "Jane", "lastname": "Doe"},
        "title": "A brief history",
    }
