# Node.js Express Article API - Developer Test

A simple REST API built with Express and Sequelize for managing articles and authors.

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
npm install
```
This installs all required packages

### Seed Database
```bash
npm run seed
```
This creates sample data for testing

### Run Tests
```bash
npm test
```
Run this to see if your tests pass.

### Run the Development Server
```bash
npm run dev
```
Run this to start the Express server at `http://localhost:3000` for manual testing

### Build for Production
```bash
npm run build
npm start
```

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

- **Express** - Fast, unopinionated web framework for Node.js
- **Sequelize** - Modern ORM for Node.js with TypeScript support
- **SQLite** - File-based database (no server required)
- **Jest** - Testing framework
- **TypeScript** - Typed superset of JavaScript

## Useful Resources
- [Express Documentation](https://expressjs.com/)
- [Sequelize Documentation](https://sequelize.org/)
- [Sequelize TypeScript Guide](https://sequelize.org/docs/v6/other-topics/typescript/)
- [Jest Documentation](https://jestjs.io/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
