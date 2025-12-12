import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../database';

export interface AuthorAttributes {
  id: number;
  firstname: string;
  lastname: string;
}

export interface AuthorCreationAttributes extends Optional<AuthorAttributes, 'id'> {}

export class Author extends Model<AuthorAttributes, AuthorCreationAttributes> implements AuthorAttributes {
  public id!: number;
  public firstname!: string;
  public lastname!: string;

  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Author.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    firstname: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    lastname: {
      type: DataTypes.STRING,
      allowNull: false,
    },
  },
  {
    sequelize,
    tableName: 'author',
    timestamps: true,
  }
);

export interface ArticleAttributes {
  id: number;
  title: string;
  author_id: number;
}

export interface ArticleCreationAttributes extends Optional<ArticleAttributes, 'id'> {}

export class Article extends Model<ArticleAttributes, ArticleCreationAttributes> implements ArticleAttributes {
  public id!: number;
  public title!: string;
  public author_id!: number;

  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Article.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    title: {
      type: DataTypes.STRING,
      allowNull: false,
      unique: true,
    },
    author_id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: Author,
        key: 'id',
      },
    },
  },
  {
    sequelize,
    tableName: 'article',
    timestamps: true,
  }
);

// Define relationships
Author.hasMany(Article, { foreignKey: 'author_id', as: 'articles' });
Article.belongsTo(Author, { foreignKey: 'author_id', as: 'author' });
