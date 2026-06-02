"""Flask route handlers for the Broken Clock application.

This module does not import app.app — no circular import risk.
It only depends on app.broken_clock (pure calculation helpers)
and app.broken_clock_storage (SQLite storage helpers).
"""

from flask import request, jsonify, render_template
from datetime import datetime

from app.broken_clock import (
    parse_hhmm,
    to_minutes,
    compute_offset,
    format_offset_human,
    compute_clock_status,
    compute_reference_points,
    format_explanation,
    format_compact_ref_point,
)
from app.broken_clock_storage import get_db_path, save_calculation, get_history


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


def find_author(author_id):
    for author in DATA["authors"]:
        if author["id"] == author_id:
            return author
    return None


def make_broken_clock_error_response(message, is_json_request, status_code=400):
    if is_json_request:
        return jsonify({"error": message}), status_code
    return render_template("broken_clock/error.html", message=message), status_code


def register_routes(app):

    @app.route("/authors")
    def get_authors():
        return jsonify(DATA["authors"])

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

        data = request.get_json() or {}
        required = ["title", "content", "author_id"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        try:
            author_id = int(data["author_id"])
        except Exception:
            return jsonify({"error": "author_id must be an integer"}), 400

        author = find_author(author_id)
        if not author:
            return jsonify({"error": "Author not found"}), 400

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
        author = find_author(author_id)
        if not author:
            return jsonify({"error": "Author not found"}), 404
        return jsonify(author)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/articles/<int:article_id>")
    def get_article(article_id):
        for article in DATA["articles"]:
            if article["id"] == article_id:
                article_with_author = article.copy()
                auth_id = int(article["author_id"])
                article_with_author["author"] = find_author(auth_id)
                article_with_author.pop("author_id", None)
                return jsonify(article_with_author)
        return jsonify({"error": "Article not found"}), 404

    @app.route("/broken-clock")
    def broken_clock_form():
        now = datetime.now()
        default_real = now.strftime("%H:%M")
        return render_template("broken_clock/form.html", default_real=default_real, nav_calculator=" is-active")

    @app.route("/broken-clock/history")
    def broken_clock_history():
        db_path = get_db_path()
        try:
            history = get_history(db_path)
        except Exception as e:
            if request.accept_mimetypes.best_match(["text/html", "application/json"]) == "text/html":
                return render_template("broken_clock/error.html", message=f"Database error: {e}"), 500
            return jsonify({"error": f"Database error: {str(e)}"}), 500

        wants_html = request.accept_mimetypes.best_match(["text/html", "application/json"]) == "text/html"

        if wants_html:
            display = history[:20]
            for r in display:
                r["ref_points_display"] = ", ".join(format_compact_ref_point(p) for p in r["reference_points"])
            return render_template(
                "broken_clock/history.html",
                records=display,
                total_count=len(history),
                nav_history=" is-active",
            ), 200

        return jsonify(history), 200

    @app.route("/broken-clock/calculate", methods=["POST"])
    def broken_clock_calculate():
        if request.is_json:
            data = request.get_json(silent=True)
        else:
            data = request.form.to_dict()

        if not data:
            return make_broken_clock_error_response("Request must be JSON or form data", request.is_json, 400)

        if "wrong_observed_time" not in data or not str(data.get("wrong_observed_time")).strip():
            return make_broken_clock_error_response("Missing required field: wrong_observed_time", request.is_json, 400)

        wrong_observed_time = data["wrong_observed_time"]

        real_observed_time = data.get("real_observed_time")
        if not real_observed_time:
            real_observed_time = datetime.now().strftime("%H:%M")

        raw_target = data.get("target_wrong_times", ["00:00", "07:00", "09:00"])
        if isinstance(raw_target, str):
            target_wrong_times = [t.strip() for t in raw_target.split(",") if t.strip()]
        elif isinstance(raw_target, list):
            target_wrong_times = raw_target
        else:
            target_wrong_times = ["00:00", "07:00", "09:00"]

        for target in target_wrong_times:
            tp = parse_hhmm(target)
            if tp is None:
                return make_broken_clock_error_response(f"Invalid target time: {target}", request.is_json, 400)

        real_p = parse_hhmm(real_observed_time)
        wrong_p = parse_hhmm(wrong_observed_time)

        if real_p is None or wrong_p is None:
            return make_broken_clock_error_response(
                "All times must be in valid HH:MM format (24-hour)", request.is_json, 400
            )

        real_minutes = to_minutes(*real_p)
        wrong_minutes = to_minutes(*wrong_p)

        offset_minutes = compute_offset(real_minutes, wrong_minutes)
        offset_human = format_offset_human(offset_minutes)
        clock_status = compute_clock_status(offset_minutes)

        reference_points = compute_reference_points(target_wrong_times, offset_minutes)

        explanation = format_explanation(offset_human, clock_status)

        try:
            db_path = get_db_path()
            save_calculation(db_path, real_observed_time, wrong_observed_time,
                             offset_minutes, offset_human, clock_status,
                             target_wrong_times, reference_points)
        except Exception as e:
            if request.is_json:
                return jsonify({"error": f"Database error: {str(e)}"}), 500
            else:
                return render_template("broken_clock/error.html", message="Could not save calculation."), 500

        if not request.is_json:
            if clock_status == "accurate":
                notif_class = "is-success"
            elif clock_status == "fast":
                notif_class = "is-warning"
            else:
                notif_class = "is-danger"
            return render_template(
                "broken_clock/result.html",
                real_observed_time=real_observed_time,
                wrong_observed_time=wrong_observed_time,
                offset_human=offset_human,
                clock_status=clock_status,
                reference_points=reference_points,
                notif_class=notif_class,
            ), 200

        return jsonify({
            "real_observed_time": real_observed_time,
            "wrong_observed_time": wrong_observed_time,
            "offset_minutes": offset_minutes,
            "offset_human": offset_human,
            "clock_status": clock_status,
            "reference_points": reference_points,
            "explanation": explanation
        }), 200
