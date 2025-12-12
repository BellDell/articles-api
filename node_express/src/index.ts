import express from 'express';
import sequelize from './database';
import { Author, Article } from './models';

const app = express();
app.use(express.json());

// Sync database
sequelize.sync({ force: false });

/**
 * GET /articles
 * Returns all articles with their authors
 */
app.get('/articles', async (req, res) => {
  try {
    // TODO: Implement this endpoint
    throw new Error('Please implement this endpoint');
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

/**
 * GET /article?id={id}
 * Returns a specific article by ID
 */
app.get('/article', async (req, res) => {
  try {
    // TODO: Implement this endpoint
    throw new Error('Please implement this endpoint');
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
