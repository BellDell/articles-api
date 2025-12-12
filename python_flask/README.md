# Python Flask Article API - Developer Test

A simple REST API built with Flask and SQLAlchemy for managing articles and authors.

## What this app does

This is a web API that manages:
- **Authors** (writers with first and last names)
- **Articles** (content pieces linked to authors)

## Development Roadmap

1. **Implement API endpoints** - Make `/articles.json` and `/article.json` work
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

### Run Tests
```bash
pytest
```
Run this to see if your tests pass.

### Run the Flask Development Server
```bash
python main.py
```
Run this to start a flask server at `http://localhost:5000` for manual testing


## API Endpoints to Implement

Currently these endpoints throw errors and need implementation:

### `GET /articles.json`
Should return all articles:
```json
[
  {
    "title": "Sample Article",
    "author": {"firstname": "John", "lastname": "Doe"}
  }
]
```

### `GET /article.json`
Should return a specific article:
```json
{
  "title": "Sample Article", 
  "author": {"firstname": "John", "lastname": "Doe"}
}
```

## Technology Stack

- **Flask** - Lightweight Python web framework
- **SQLAlchemy** - Database toolkit and ORM (Object-Relational Mapping)
- **SQLite** - File-based database (no server required)
- **pytest** - Testing framework

## Usesful Resources
- [Flask-SQLAlchemy Quickstart](https://flask-sqlalchemy.palletsprojects.com/quickstart/)
- [Querying Records](https://flask-sqlalchemy.palletsprojects.com/queries/#querying-records)
- [Accessing request params](http://flask.pocoo.org/quickstart/#the-request-object)
- [Creating json responses](https://flask.palletsprojects.com/api/#flask.json.jsonify)
- [Defining Models](https://flask-sqlalchemy.palletsprojects.com/models/)
- [Relationships](https://flask-sqlalchemy.palletsprojects.com/models/#one-to-many-relationships)
- [Query API](https://flask-sqlalchemy.palletsprojects.com/queries/)
- [Database Operations](https://flask-sqlalchemy.palletsprojects.com/quickstart/#create-the-tables)
- [Filtering & Ordering](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html#filtering)
- [Flask Testing](https://flask.palletsprojects.com/en/3.0.x/testing/)
- [Testing Database Code](https://flask-sqlalchemy.palletsprojects.com/contexts/)
