#!/usr/bin/env python3
"""
Script to seed the database with test data
"""

from main import engine, Author, Article, SQLModel
from sqlmodel import Session

def seed_database():
    """Create tables and add some sample data."""
    # Create tables
    SQLModel.metadata.create_all(bind=engine)
    
    # Create session
    with Session(engine) as db:
        try:
            # Check if data already exists
            from sqlmodel import select
            existing_authors = db.exec(select(Author)).all()
            if existing_authors:
                print("Database already has data. Skipping seed.")
                return
            
            # Create authors
            authors = [
                Author(firstname="Jane", lastname="Doe"),
                Author(firstname="John", lastname="Smith"),
                Author(firstname="Alice", lastname="Johnson"),
            ]
            
            for author in authors:
                db.add(author)
            
            db.commit()
            
            # Refresh to get IDs
            for author in authors:
                db.refresh(author)
            
            # Create articles
            articles = [
                Article(title="A brief history of programming", author_id=authors[0].id),
                Article(title="The future of AI", author_id=authors[1].id),
                Article(title="Web development best practices", author_id=authors[2].id),
                Article(title="Database design patterns", author_id=authors[0].id),
            ]
            
            for article in articles:
                db.add(article)
            
            db.commit()
            
            print("Database seeded successfully!")
            print(f"Created {len(authors)} authors and {len(articles)} articles.")
            
        except Exception as e:
            print(f"Error seeding database: {e}")
            db.rollback()

if __name__ == "__main__":
    seed_database()