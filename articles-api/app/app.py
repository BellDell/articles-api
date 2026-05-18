from flask import Flask, request, jsonify
import os
import sys

app = Flask(__name__)

DATA = {
    "authors": [
        {
            "author": {
                "id": 1,
                "first_name": "John",
                "last_name": "Doe",
            }
        },
        {
            "author": {
                "id": 2,
                "first_name": "Alise",
                "last_name": "Bean",
            }
        }
    ],
    "articles": [
        {
            "id": 1,
            "title": "A brief history",
            "content": "Some article content",
            "author_id": 1,
        },
        {
            "id": 2,
            "title": "A long history",
            "content": "More article content",
            "author_id": 1,
        },
    ],
}


@app.route("/authors")
def get_authors():
    return DATA["authors"]


# @app.route("/articles")
# def get_articles():
#     for article in DATA["articles"]:
#         article["author"] = find_author(article["author_id"])
#         yield article



@app.route("/author/<int:author_id>")
def author(author_id):
    """Get the author of the article."""
    author = find_author(author_id)
    if not author:
        return jsonify({"error": "Author not found"}), 404
    return jsonify({author})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/articles/<int:article_id>")
def get_article(article_id):
    """Get a specific article by ID."""

    for article in DATA["articles"]:
        if article["id"] == article_id:
            article_with_author = article.copy()

            auth_id = int(article["author_id"])
            article_with_author["author"] = find_author(auth_id)
            article_with_author.pop("author_id", None)

            return jsonify(article_with_author)

    return jsonify({"error": "Article not found"}), 404



def find_author(author_id:int):
    for author in DATA["authors"]:
        if author["author"]["id"] == author_id:
            return author
    return None


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
