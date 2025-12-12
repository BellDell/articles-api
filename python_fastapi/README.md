# Python FastAPI Article API - Developer Test

A simple REST API built with FastAPI for managing articles and authors.

## What this app does

This is a web API that manages:
- **Authors** (writers with first and last names)
- **Articles** (content pieces linked to authors)

## Development Roadmap

1. **Implement API endpoints** - Make `/articles` and `/article` work
2. **Write unit tests** - Test your endpoints return correct data
3. **Create a frontend** - Build a web interface that calls your API
4. **Display articles list** - Show all articles ordered by title
5. **Integration tests** - Test the full flow from database to frontend
6. **Article details page** - Show individual article information
7. **Author details page** - Display author information and their articles
8. **Link articles to authors** - Ensure proper relationships work
9. **Multiple authors** - Allow articles to have multiple authors
10. **Edit functionality** - Let users modify article details
11. **Test editing** - Ensure edit functionality works correctly

### Install Dependencies
```bash
pipenv install
pipenv shell
```
This creates and enters a virtual environment while installing all required packages

### Seed Database
```bash
python seed.py
```
This creates sample data for testing

### Run Tests
```bash
pytest
```
Run this to see if your tests pass.

### Run the FastAPI Development Server
```bash
python main.py
```
Run this to start a FastAPI server at `http://localhost:8000` for manual testing

### View API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

## API Endpoints

### `GET /articles`
Returns all articles with their authors:
```json
[
  {
    "id": 1,
    "title": "Sample Article",
    "author": {"id": 1, "firstname": "John", "lastname": "Doe"}
  }
]
```

### `GET /article?id={id}`
Returns a specific article by ID:
```json
{
  "id": 1,
  "title": "Sample Article", 
  "author": {"id": 1, "firstname": "John", "lastname": "Doe"}
}
```

## Technology Stack

- **FastAPI** - Modern, fast Python web framework with automatic API documentation
- **SQLModel** - Combines SQLAlchemy and Pydantic for type-safe database models
- **SQLite** - File-based database (no server required)
- **pytest** - Testing framework
- **Pydantic** - Data validation and serialization (integrated with SQLModel)

## Useful Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [SQLModel Tutorial](https://sqlmodel.tiangolo.com/tutorial/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)