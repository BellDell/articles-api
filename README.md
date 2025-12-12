# Practical Developer Test

This repository contains different versions of the same Article API, allowing candidates to choose their preferred technology stack.

## Serving suggestions
This exercise is best done as a pair programming session, usually lasting 60-120 minutes.

## What we are looking for
- Strong programming fundamentals
- Aptitude for troubleshooting
- Good dialogue! (How you communicate and collaborate in a development context)

## What we are not looking for
We are not expecting a fully working application nor high test coverage. 

## Choose Your Framework

### Python (FastAPI + SQLModel)
**Location:** `python_fastapi/`

**Tech Stack:**
- Python 3.12+
- FastAPI
- SQLModel
- pytest

**Quick Start:**
```bash
cd python_fastapi
pipenv install
pipenv shell
python seed.py
pytest
python main.py
```

### Python (Flask + SQLAlchemy)
**Location:** `python_flask/`

**Tech Stack:**
- Python 3.12+
- Flask
- SQL Alchemy
- pytest

**Quick Start:**
```bash
cd python_flask
pipenv install
pipenv shell
python seed.py
pytest
python main.py
```

### Node.js (Express + Sequelize)
**Location:** `node_express/`

**Tech Stack:**
- Node.js 18+
- Express
- Sequelize ORM
- Jest


**Quick Start:**
```bash
cd node_express
npm install
npm run seed
npm test
npm run dev
```

## Test Requirements

Both versions have the same requirements:

1. **Implement an endpoint for fetching articles** - Return all articles with their authors
2. **Implement an endpoint for fetching a specific article** - Return a specific article by ID with its author
3. **Pass all tests** - Ensure your implementation works correctly
4. **Handle errors** - Return appropriate HTTP status codes

Once you've done those things, you're welcome to go any direction you like. Consider:
- Frontend development
- Adding more endpoints for Creating, Updating or Deleting records
- More rigorous testing

## What You'll Be Building

A simple REST API that manages:
- **Authors** (writers with first and last names)
- **Articles** (content pieces linked to authors)

## Database

Both versions use SQLite, so no database server setup is required. The database file is created automatically when you run the seed script.

Good luck! 🚀
