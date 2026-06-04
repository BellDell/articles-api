"""Flask route handlers for the Broken Clock application.

This module does not import app.app — no circular import risk.
It only depends on app.broken_clock (pure calculation helpers)
and app.broken_clock_storage (SQLite storage helpers).
"""

from flask import request, jsonify, render_template, redirect
from datetime import datetime

from app.broken_clock.domain import (
    parse_hhmm,
    to_minutes,
    compute_offset,
    format_offset_human,
    compute_clock_status,
    compute_reference_points,
    format_explanation,
    format_compact_ref_point,
)
from app.broken_clock.storage import get_db_path, save_calculation, get_history, delete_history_record
from app.water_meter import storage as wm_storage
from app.water_meter.domain import validate_reading
from app.core.rate_limit import consume_write_quota
from app.core.rate_limit.limiter import make_429_response, WINDOW_SECONDS, MAX_WRITES


BROKEN_CLOCK_ERROR_TEMPLATE = "broken_clock/error.html"
BROKEN_CLOCK_RESULT_TEMPLATE = "broken_clock/result.html"
BROKEN_CLOCK_FORM_TEMPLATE = "broken_clock/form.html"
BROKEN_CLOCK_HISTORY_TEMPLATE = "broken_clock/history.html"
TEXT_HTML = "text/html"
APPLICATION_JSON = "application/json"
ACCEPT_PREFERENCE = [TEXT_HTML, APPLICATION_JSON]


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
    return render_template(BROKEN_CLOCK_ERROR_TEMPLATE, message=message), status_code


def _parse_request_data():
    """Extract and validate input data from a broken-clock request."""
    if request.is_json:
        data = request.get_json(silent=True)
    else:
        data = request.form.to_dict()

    if not data:
        return make_broken_clock_error_response(
            "Request must be JSON or form data", request.is_json, 400
        ), None, None, None

    if "wrong_observed_time" not in data or not str(data.get("wrong_observed_time")).strip():
        return make_broken_clock_error_response(
            "Missing required field: wrong_observed_time", request.is_json, 400
        ), None, None, None

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
            return make_broken_clock_error_response(
                f"Invalid target time: {target}", request.is_json, 400
            ), None, None, None

    return None, real_observed_time, wrong_observed_time, target_wrong_times


def _notification_class(clock_status):
    if clock_status == "accurate":
        return "is-success"
    elif clock_status == "fast":
        return "is-warning"
    return "is-danger"


# ---------------------------------------------------------------------------
# Route handlers (module-level)
# ---------------------------------------------------------------------------

def get_authors():
    return jsonify(DATA["authors"])


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


def get_author(author_id):
    author = find_author(author_id)
    if not author:
        return jsonify({"error": "Author not found"}), 404
    return jsonify(author)


def health():
    return jsonify({"status": "ok"})


def get_article(article_id):
    for article in DATA["articles"]:
        if article["id"] == article_id:
            article_with_author = article.copy()
            auth_id = int(article["author_id"])
            article_with_author["author"] = find_author(auth_id)
            article_with_author.pop("author_id", None)
            return jsonify(article_with_author)
    return jsonify({"error": "Article not found"}), 404


def home():
    return render_template("broken_clock/home.html", active_page="home")


def broken_clock_form():
    now = datetime.now()
    default_real = now.strftime("%H:%M")
    return render_template(BROKEN_CLOCK_FORM_TEMPLATE, default_real=default_real, active_page="calculator")


def broken_clock_history():
    db_path = get_db_path()
    try:
        history = get_history(db_path)
    except Exception as e:
        if request.accept_mimetypes.best_match(ACCEPT_PREFERENCE) == TEXT_HTML:
            return render_template(BROKEN_CLOCK_ERROR_TEMPLATE, message=f"Database error: {e}"), 500
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    wants_html = request.accept_mimetypes.best_match(ACCEPT_PREFERENCE) == TEXT_HTML

    if wants_html:
        display = history[:20]
        for r in display:
            r["ref_points_display"] = ", ".join(format_compact_ref_point(p) for p in r["reference_points"])
        return render_template(
            BROKEN_CLOCK_HISTORY_TEMPLATE,
            records=display,
            total_count=len(history),
            active_page="history",
        ), 200

    return jsonify(history), 200


def broken_clock_calculate():
    err, real_observed_time, wrong_observed_time, target_wrong_times = _parse_request_data()
    if err:
        return err

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

    # Rate limit check — after validation, before DB write
    allowed, retry_after = consume_write_quota("broken_clock", request.remote_addr)
    if not allowed:
        if request.is_json:
            return make_429_response()
        return render_template(
            BROKEN_CLOCK_ERROR_TEMPLATE,
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        ), 429

    try:
        db_path = get_db_path()
        save_calculation(db_path, real_observed_time, wrong_observed_time,
                         offset_minutes, offset_human, clock_status,
                         target_wrong_times, reference_points)
    except Exception as e:
        if request.is_json:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        else:
            return render_template(BROKEN_CLOCK_ERROR_TEMPLATE, message="Could not save calculation."), 500

    if not request.is_json:
        return render_template(
            BROKEN_CLOCK_RESULT_TEMPLATE,
            real_observed_time=real_observed_time,
            wrong_observed_time=wrong_observed_time,
            offset_human=offset_human,
            clock_status=clock_status,
            reference_points=reference_points,
            notif_class=_notification_class(clock_status),
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


def delete_history(record_id):
    """DELETE /broken-clock/history/<record_id> — JSON API."""
    db_path = get_db_path()
    try:
        deleted = delete_history_record(record_id, db_path)
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    if not deleted:
        return jsonify({"error": "History record not found", "id": record_id}), 404

    return jsonify({"deleted": True, "id": record_id}), 200


def delete_history_html(record_id):
    """POST /broken-clock/history/<record_id>/delete — HTML form fallback."""
    db_path = get_db_path()
    try:
        deleted = delete_history_record(record_id, db_path)
    except Exception as e:
        return render_template(BROKEN_CLOCK_ERROR_TEMPLATE, message=f"Database error: {e}"), 500

    if not deleted:
        return render_template(BROKEN_CLOCK_ERROR_TEMPLATE, message="History record not found."), 404

    return redirect("/broken-clock/history")


def water_meter_form():
    today = datetime.now().strftime("%Y-%m-%d")
    db_path = wm_storage.get_db_path()
    meter_names = wm_storage.get_meter_names(db_path)
    return render_template("water_meter/form.html", default_reading_date=today,
                           meter_names=meter_names, active_page="water_meter")


def water_meter_add_reading():
    if request.is_json:
        data = request.get_json(silent=True)
    else:
        data = request.form.to_dict()

    errors, cleaned = validate_reading(
        reading_value=data.get("reading_value"),
        reading_date=data.get("reading_date"),
        meter_name=data.get("meter_name"),
        unit=data.get("unit"),
        notes=data.get("notes"),
    )
    if errors:
        msg = "; ".join(errors.values())
        if request.is_json:
            return jsonify({"error": msg}), 400
        return redirect(f"/water-meter?error={msg}&reading_date={data.get('reading_date', '')}&meter_name={data.get('meter_name', '')}&unit={data.get('unit', '')}&notes={data.get('notes', '')}")

    # Rate limit check — after validation, before DB write
    allowed, retry_after = consume_write_quota("water_meter", request.remote_addr)
    if not allowed:
        if request.is_json:
            return make_429_response()
        return render_template(
            "broken_clock/error.html",
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        ), 429

    db_path = wm_storage.get_db_path()
    try:
        wm_storage.save_reading(
            db_path,
            reading_value=cleaned["reading_value"],
            reading_date=cleaned["reading_date"],
            meter_name=cleaned["meter_name"],
            unit=cleaned["unit"],
            notes=cleaned["notes"],
        )
    except Exception as e:
        if request.is_json:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        return render_template("broken_clock/error.html", message="Could not save reading."), 500

    if request.is_json:
        return jsonify({"success": True}), 201
    return redirect("/water-meter/history")


def water_meter_history():
    db_path = wm_storage.get_db_path()
    try:
        readings = wm_storage.get_readings(db_path)
    except Exception as e:
        if request.accept_mimetypes.best_match(ACCEPT_PREFERENCE) == TEXT_HTML:
            return render_template("broken_clock/error.html", message=f"Database error: {e}"), 500
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    if request.accept_mimetypes.best_match(ACCEPT_PREFERENCE) == APPLICATION_JSON:
        return jsonify(readings), 200
    return render_template("water_meter/history.html", readings=readings, active_page="water_meter"), 200


def delete_water_meter_reading(record_id):
    """DELETE /water-meter/readings/<record_id> — JSON API."""
    db_path = wm_storage.get_db_path()
    try:
        deleted = wm_storage.delete_reading(record_id, db_path)
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    if not deleted:
        return jsonify({"error": "Reading not found", "id": record_id}), 404

    return jsonify({"deleted": True, "id": record_id}), 200


def delete_water_meter_reading_html(record_id):
    """POST /water-meter/readings/<record_id>/delete — HTML form fallback."""
    db_path = wm_storage.get_db_path()
    try:
        deleted = wm_storage.delete_reading(record_id, db_path)
    except Exception as e:
        return render_template("broken_clock/error.html", message=f"Database error: {e}"), 500

    if not deleted:
        return render_template("broken_clock/error.html", message="Reading not found."), 404

    return redirect("/water-meter/history")


def register_routes(app):
    app.add_url_rule("/", endpoint="home", view_func=home)
    app.add_url_rule("/authors", endpoint="get_authors", view_func=get_authors)
    app.add_url_rule(
        "/articles", endpoint="get_articles", view_func=get_articles,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/author/<int:author_id>", endpoint="get_author", view_func=get_author,
    )
    app.add_url_rule("/health", endpoint="health", view_func=health)
    app.add_url_rule(
        "/articles/<int:article_id>", endpoint="get_article", view_func=get_article,
    )
    app.add_url_rule(
        "/broken-clock", endpoint="broken_clock_form", view_func=broken_clock_form,
    )
    app.add_url_rule(
        "/broken-clock/history", endpoint="broken_clock_history",
        view_func=broken_clock_history,
    )
    app.add_url_rule(
        "/broken-clock/calculate", endpoint="broken_clock_calculate",
        view_func=broken_clock_calculate, methods=["POST"],
    )
    app.add_url_rule(
        "/broken-clock/history/<record_id>", endpoint="delete_history",
        view_func=delete_history, methods=["DELETE"],
    )
    app.add_url_rule(
        "/broken-clock/history/<record_id>/delete", endpoint="delete_history_html",
        view_func=delete_history_html, methods=["POST"],
    )
    app.add_url_rule("/water-meter", endpoint="water_meter_form", view_func=water_meter_form)
    app.add_url_rule(
        "/water-meter/readings", endpoint="water_meter_add_reading",
        view_func=water_meter_add_reading, methods=["POST"],
    )
    app.add_url_rule("/water-meter/history", endpoint="water_meter_history", view_func=water_meter_history)
    app.add_url_rule(
        "/water-meter/readings/<record_id>", endpoint="delete_water_meter_reading",
        view_func=delete_water_meter_reading, methods=["DELETE"],
    )
    app.add_url_rule(
        "/water-meter/readings/<record_id>/delete", endpoint="delete_water_meter_reading_html",
        view_func=delete_water_meter_reading_html, methods=["POST"],
    )
