import os
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship

# Database setup
db_path = os.path.join(os.path.dirname(__file__), "mock_data.sqlitedb")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Database dependency
def get_db():
    with Session(engine) as session:
        yield session

# FastAPI app
app = FastAPI(title="Article API", description="A simple article management API")

"""
SQLModel definitions
"""

class AuthorBase(SQLModel):
    firstname: str
    lastname: str

class Author(AuthorBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationship
    articles: List["Article"] = Relationship(back_populates="author")

class AuthorResponse(AuthorBase):
    id: int

class ArticleBase(SQLModel):
    title: str = Field(unique=True)
    author_id: int = Field(foreign_key="author.id")

class Article(ArticleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationship
    author: Optional[Author] = Relationship(back_populates="articles")

class ArticleResponse(ArticleBase):
    id: int
    author: AuthorResponse

"""
API endpoints
"""

@app.get("/articles", response_model=List[ArticleResponse])
def get_articles(db: Session = Depends(get_db)):
    """Get all articles with their authors."""
    """Implement this method please"""
    raise Exception("please implement")

@app.get("/article", response_model=ArticleResponse)
def get_article(id: int, db: Session = Depends(get_db)):
    """Get a specific article by ID."""
    """Implement this method please"""
    raise Exception("please implement")

"""
Database initialization
"""

def create_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_tables()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)