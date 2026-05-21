from flask import Flask, request, jsonify
import os
import sys

app = Flask(__name__)

DATA = {
    "authors": [
        {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
        },
        {
            "id": 2,
            "first_name": "Alise",
            "last_name": "Bean",
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
    return jsonify(DATA["authors"])  # ensure JSON response


@app.route("/articles", methods=["GET", "POST"])
def get_articles():
    if request.method == "GET":
        articles_with_authors = []
        for article in DATA["articles"]:
            article_copy = article.copy()
            article_copy["author"] = find_author(article_copy["author_id"]) 
            article_copy.pop("author_id", None)
            articles_with_authors.append(article_copy)
        return jsonify(articles_with_authors)

    # POST - create a new article
    data = request.get_json() or {}
    required = ["title", "content", "author_id"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # validate author exists
    try:
        author_id = int(data["author_id"])
    except Exception:
        return jsonify({"error": "author_id must be an integer"}), 400

    author = find_author(author_id)
    if not author:
        return jsonify({"error": "Author not found"}), 400

    # create new article id
    next_id = 1
    if DATA["articles"]:
        next_id = max(a["id"] for a in DATA["articles"]) + 1

    new_article = {
        "id": next_id,
        "title": data["title"],
        "content": data["content"],
        "author_id": author_id,
    }
    DATA["articles"].append(new_article)

    resp = new_article.copy()
    resp["author"] = author
    resp.pop("author_id", None)

    return jsonify(resp), 201


@app.route("/author/<int:author_id>")
def author(author_id):
    """Get the author by id."""
    author = find_author(author_id)
    if not author:
        return jsonify({"error": "Author not found"}), 404
    return jsonify(author)


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


@app.route("/articles/<int:article_id>", methods=["DELETE"])
def delete_article(article_id):
    """Delete an article by ID."""
    for idx, article in enumerate(DATA["articles"]):
        if article["id"] == article_id:
            # remove the article
            DATA["articles"].pop(idx)
            return ("", 204)
    return jsonify({"error": "Article not found"}), 404


def find_author(author_id:int):
    for author in DATA["authors"]:
        if author["id"] == author_id:
            return author
    return None


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
