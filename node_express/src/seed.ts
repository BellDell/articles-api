import sequelize from './database';
import { Author, Article } from './models';

async function seedDatabase() {
  try {
    // Sync database (creates tables if they don't exist)
    await sequelize.sync({ force: false });

    // Check if data already exists
    const existingAuthors = await Author.findAll();
    if (existingAuthors.length > 0) {
      console.log('Database already has data. Skipping seed.');
      return;
    }

    // Create authors
    const authors = await Author.bulkCreate([
      { firstname: 'Jane', lastname: 'Doe' },
      { firstname: 'John', lastname: 'Smith' },
      { firstname: 'Alice', lastname: 'Johnson' },
    ]);

    console.log(`Created ${authors.length} authors`);

    // Create articles
    const articles = await Article.bulkCreate([
      { title: 'A brief history of programming', author_id: authors[0].id },
      { title: 'The future of AI', author_id: authors[1].id },
      { title: 'Web development best practices', author_id: authors[2].id },
      { title: 'Database design patterns', author_id: authors[0].id },
    ]);

    console.log(`Created ${articles.length} articles`);
    console.log('Database seeded successfully!');
  } catch (error) {
    console.error('Error seeding database:', error);
  } finally {
    await sequelize.close();
  }
}

seedDatabase();
