import { Sequelize } from 'sequelize';
import path from 'path';

const dbPath = path.join(__dirname, '../mock_data.sqlitedb');

const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: dbPath,
  logging: false,
});

export default sequelize;
