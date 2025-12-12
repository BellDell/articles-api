import request from 'supertest';
import express from 'express';
import sequelize from './database';
import { Author, Article } from './models';

describe('Article API Tests', () => {
  let app: express.Application;

  beforeAll(async () => {
    // Create Express app for testing
    app = express();
    app.use(express.json());

    // Sync database
    await sequelize.sync({ force: true });

    // Mock the routes (candidates will implement these)
    app.get('/articles', async (req, res) => {
      try {
        throw new Error('Please implement this endpoint');
      } catch (error) {
        res.status(500).json({ error: (error as Error).message });
      }
    });

    app.get('/article', async (req, res) => {
      try {
        throw new Error('Please implement this endpoint');
      } catch (error) {
        res.status(500).json({ error: (error as Error).message });
      }
    });
  });

  afterEach(async () => {
    // Clean up database after each test
    await Article.destroy({ where: {} });
    await Author.destroy({ where: {} });
  });

  afterAll(async () => {
    await sequelize.close();
  });

  test('GET /articles - returns all articles with authors', async () => {
    // Create test data
    const jane = await Author.create({
      firstname: 'Jane',
      lastname: 'Doe',
    });

    await Article.create({
      title: 'A brief history',
      author_id: jane.id,
    });

    // Test the endpoint
    const response = await request(app).get('/articles');

    expect(response.status).toBe(200);
    expect(response.body).toBeInstanceOf(Array);
    expect(response.body.length).toBe(1);
    expect(response.body[0]).toHaveProperty('title', 'A brief history');
    expect(response.body[0]).toHaveProperty('author');
    expect(response.body[0].author).toHaveProperty('firstname', 'Jane');
    expect(response.body[0].author).toHaveProperty('lastname', 'Doe');
  });

  test('GET /article?id={id} - returns specific article', async () => {
    // Create test data
    const jane = await Author.create({
      firstname: 'Jane',
      lastname: 'Doe',
    });

    const article = await Article.create({
      title: 'A brief history',
      author_id: jane.id,
    });

    // Test the endpoint
    const response = await request(app).get(`/article?id=${article.id}`);

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('title', 'A brief history');
    expect(response.body).toHaveProperty('author');
    expect(response.body.author).toHaveProperty('firstname', 'Jane');
    expect(response.body.author).toHaveProperty('lastname', 'Doe');
  });

  test('GET /article?id={id} - returns 404 for non-existent article', async () => {
    const response = await request(app).get('/article?id=999');

    expect(response.status).toBe(404);
    expect(response.body).toHaveProperty('error', 'Article not found');
  });
});
