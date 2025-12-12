import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session
from main import app, get_db, Author, Article, SQLModel

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

def override_get_db():
    with Session(engine) as session:
        yield session

@pytest.fixture(scope="function")
def db_session():
    """Creates a new database session for a test."""
    # Create tables before each test
    SQLModel.metadata.create_all(bind=engine)
    with Session(engine) as db:
        yield db
    # Clean up after each test
    SQLModel.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    # Override the database dependency for testing
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

def test_articles(db_session, client):
    # Create test data
    jane = Author(firstname="Jane", lastname="Doe")
    db_session.add(jane)
    db_session.commit()
    db_session.refresh(jane)
    
    brief = Article(title="A brief history", author_id=jane.id)
    db_session.add(brief)
    db_session.commit()
    
    # Test the endpoint
    response = client.get("/articles")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "A brief history"
    assert data[0]["author"]["firstname"] == "Jane"
    assert data[0]["author"]["lastname"] == "Doe"

def test_article_by_id(db_session, client):
    # Create test data
    jane = Author(firstname="Jane", lastname="Doe")
    db_session.add(jane)
    db_session.commit()
    db_session.refresh(jane)
    
    brief = Article(title="A brief history", author_id=jane.id)
    db_session.add(brief)
    db_session.commit()
    db_session.refresh(brief)
    
    # Test the endpoint
    response = client.get(f"/article?id={brief.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "A brief history"
    assert data["author"]["firstname"] == "John"
    assert data["author"]["lastname"] == "Doe"

def test_article_not_found(db_session, client):
    """Test that 404 is returned for non-existent article."""
    response = client.get("/article?id=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"

def test_create_author(db_session, client):
    """Test that an author can be created."""
    response = client.post("/authors", json={
        "firstname": "John",
        "lastname": "Doe"
    })
    assert response.status_code == 200
    assert response.json()["firstname"] == "John"
    assert response.json()["lastname"] == "Doe"

def test_update_author(db_session, client):
    """Test that an author can be updated."""
    
    
def test_create_article(db_session, client):
    """Test that an article can be created."""
    response = client.post("/articles", json={
        "title": "A new article",
        "author_id": 1
    })
    assert response.status_code == 200
    assert response.json()["title"] == "A new article"
    assert response.json()["author_id"] == 1
    assert response.json()["author"]["firstname"] == "John"
    assert response.json()["author"]["lastname"] == "Doe"
    
    # What if the author doesn't exist?...