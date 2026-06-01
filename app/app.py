from flask import Flask, request, jsonify
import os
import sys
import sqlite3
import json
from datetime import datetime, timezone

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


def find_author(author_id:int):
    for author in DATA["authors"]:
        if author["id"] == author_id:
            return author
    return None


@app.route("/broken-clock")
def broken_clock_form():
    """Show a simple HTML form for the Broken Clock Calculator."""
    now = datetime.now()
    default_real = now.strftime("%H:%M")
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Broken Clock Calculator</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
</head>
<body>
  <section class="section">
    <div class="container">
      <div class="box">
        <h1 class="title">Broken Clock Calculator</h1>
        <p class="subtitle">Find out what time it really is when a clock is running fast or slow. Enter both times right now, then list the broken-clock readings you want to look up.</p>
        <form action="/broken-clock/calculate" method="post">
          <div class="field">
            <label class="label">Actual time right now (HH:MM)</label>
            <div class="control">
              <input class="input" type="text" name="real_observed_time" value="{default_real}" placeholder="HH:MM">
            </div>
            <p class="help">What the real clock, phone, or computer shows right now.</p>
          </div>
          <div class="field">
            <label class="label">What the broken clock shows right now (HH:MM)</label>
            <div class="control">
              <input class="input" type="text" name="wrong_observed_time" value="10:00" placeholder="HH:MM">
            </div>
          </div>
          <div class="field">
            <label class="label">Broken-clock times to look up (comma-separated)</label>
            <div class="control">
              <input class="input" type="text" name="target_wrong_times" value="00:00,07:00,09:00" placeholder="00:00,07:00,09:00">
            </div>
            <p class="help">When the broken clock shows these times, what is the real time? For example: alarms or schedules.</p>
          </div>
          <div class="field">
            <div class="control">
              <button class="button is-primary" type="submit">Calculate real times</button>
            </div>
          </div>
          <p class="is-size-7 mt-2"><a href="/broken-clock/history">View calculation history</a></p>
        </form>
      </div>
    </div>
  </section>
</body>
</html>
"""


def get_db_path():
    return os.environ.get("APP_DB_PATH", "data/app.db")


def ensure_db_initialized(db_path):
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broken_clock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                real_observed_time TEXT NOT NULL,
                wrong_observed_time TEXT NOT NULL,
                offset_minutes INTEGER NOT NULL,
                offset_human TEXT NOT NULL,
                clock_status TEXT NOT NULL,
                target_wrong_times_json TEXT NOT NULL,
                reference_points_json TEXT NOT NULL
            )
        """)


def save_calculation(db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points):
    ensure_db_initialized(db_path)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO broken_clock_history
               (created_at, real_observed_time, wrong_observed_time,
                offset_minutes, offset_human, clock_status,
                target_wrong_times_json, reference_points_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (created_at, real_observed_time, wrong_observed_time,
             offset_minutes, offset_human, clock_status,
             json.dumps(target_wrong_times), json.dumps(reference_points))
        )


def get_history(db_path):
    ensure_db_initialized(db_path)
    rows = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM broken_clock_history ORDER BY created_at DESC"
        )
        for row in cursor.fetchall():
            rows.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "real_observed_time": row["real_observed_time"],
                "wrong_observed_time": row["wrong_observed_time"],
                "offset_minutes": row["offset_minutes"],
                "offset_human": row["offset_human"],
                "clock_status": row["clock_status"],
                "target_wrong_times": json.loads(row["target_wrong_times_json"]),
                "reference_points": json.loads(row["reference_points_json"]),
            })
    return rows


@app.route("/broken-clock/history")
def broken_clock_history():
    db_path = get_db_path()
    try:
        history = get_history(db_path)
    except Exception as e:
        if request.accept_mimetypes.best_match(["text/html", "application/json"]) == "text/html":
            return f"""<!DOCTYPE html>
<html><head><title>Error</title></head>
<body><h1>500 Database Error</h1><p>{e}</p></body></html>""", 500, {'Content-Type': 'text/html'}
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    wants_html = request.accept_mimetypes.best_match(["text/html", "application/json"]) == "text/html"

    if wants_html:
        if not history:
            rows_display = """<div class="notification is-info">
  No calculations yet. <a href="/broken-clock">Go back</a> to run your first calculation.
</div>"""
        else:
            limit = 20
            display = history[:limit]
            rows_html = ""
            for r in display:
                ref_points = ", ".join(
                    _compact_ref_point(p) for p in r["reference_points"]
                )
                rows_html += f"""<tr>
  <td>{r["created_at"]}</td>
  <td>{r["real_observed_time"]}</td>
  <td>{r["wrong_observed_time"]}</td>
  <td>{r["offset_human"]}</td>
  <td>{r["clock_status"]}</td>
  <td>{ref_points}</td>
</tr>"""
            note = ""
            if len(history) > limit:
                note = f"<p class=\"is-size-7\">Showing latest {limit} calculations, newest first.</p>"
            rows_display = f"""
<table class="table is-striped is-fullwidth is-narrow">
  <thead>
    <tr>
      <th>When</th>
      <th>Actual time observed</th>
      <th>Broken clock showed</th>
      <th>Offset</th>
      <th>Status</th>
      <th>Reference points</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>
<p class="is-size-7">Showing latest {len(display)} calculations, newest first.</p>
"""
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Calculation History</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
</head>
<body>
  <section class="section">
    <div class="container">
      <div class="box">
        <h1 class="title">Calculation History</h1>
        {rows_display}
        <a class="button is-primary mt-3" href="/broken-clock">← Calculate again</a>
      </div>
    </div>
  </section>
</body>
</html>
"""
        return html, 200, {'Content-Type': 'text/html'}

    return jsonify(history), 200


def _compact_ref_point(rp):
    label = f"{rp['wrong_time']} \u2192 {rp['real_time']}"
    if rp["day_shift"] == 1:
        label += " (next day)"
    elif rp["day_shift"] == -1:
        label += " (previous day)"
    return label


def make_broken_clock_error_response(message, is_json_request, status_code=400):
    if is_json_request:
        return jsonify({"error": message}), status_code
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Error</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
</head>
<body>
  <section class="section">
    <div class="container">
      <div class="box">
        <h1 class="title">Error</h1>
        <div class="notification is-danger">{message}</div>
        <a class="button is-primary" href="/broken-clock">← Calculate again</a>
      </div>
    </div>
  </section>
</body>
</html>
"""
    return html, status_code, {'Content-Type': 'text/html'}


@app.route("/broken-clock/calculate", methods=["POST"])
def broken_clock_calculate():
    """Calculate broken clock offset and target times.

    Accept either JSON or form submissions. For form submissions return an HTML
    result page; for JSON return a JSON response.
    """
    # Load data: prefer JSON when declared, otherwise fall back to form data
    if request.is_json:
        data = request.get_json(silent=True)
    else:
        data = request.form.to_dict()

    if not data:
        return make_broken_clock_error_response("Request must be JSON or form data", request.is_json, 400)

    # Required field: wrong_observed_time
    if "wrong_observed_time" not in data or not str(data.get("wrong_observed_time")).strip():
        return make_broken_clock_error_response("Missing required field: wrong_observed_time", request.is_json, 400)

    wrong_observed_time = data["wrong_observed_time"]

    # real_observed_time optional: default to current system time HH:MM
    real_observed_time = data.get("real_observed_time")
    if not real_observed_time:
        real_observed_time = datetime.now().strftime("%H:%M")

    # target_wrong_times optional: accept list or comma string
    raw_target = data.get("target_wrong_times", ["00:00", "07:00", "09:00"]) 
    if isinstance(raw_target, str):
        target_wrong_times = [t.strip() for t in raw_target.split(",") if t.strip()]
    elif isinstance(raw_target, list):
        target_wrong_times = raw_target
    else:
        target_wrong_times = ["00:00", "07:00", "09:00"]

    # Helper to parse HH:MM
    def parse_hhmm(s):
        try:
            parts = s.split(":")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return h, m
        except (ValueError, IndexError, AttributeError):
            return None

    def to_minutes(h, m):
        return h * 60 + m

    # Parse real and wrong
    real_p = parse_hhmm(real_observed_time)
    wrong_p = parse_hhmm(wrong_observed_time)

    if real_p is None or wrong_p is None:
        return make_broken_clock_error_response("All times must be in valid HH:MM format (24-hour)", request.is_json, 400)

    real_minutes = to_minutes(*real_p)
    wrong_minutes = to_minutes(*wrong_p)

    # Compute offset: shortest difference between wrong and real
    raw_diff = wrong_minutes - real_minutes

    if raw_diff > 720:
        offset_minutes = raw_diff - 1440
    elif raw_diff < -720:
        offset_minutes = raw_diff + 1440
    else:
        offset_minutes = raw_diff

    # Human-readable offset
    if offset_minutes >= 0:
        offset_human = f"+{offset_minutes} minutes"
    else:
        offset_human = f"{offset_minutes} minutes"

    # Clock status
    if offset_minutes > 0:
        clock_status = "fast"
    elif offset_minutes < 0:
        clock_status = "slow"
    else:
        clock_status = "accurate"

    # Build reference points
    reference_points = []
    for target in target_wrong_times:
        tp = parse_hhmm(target)
        if tp is None:
            return make_broken_clock_error_response(f"Invalid target time: {target}", request.is_json, 400)
        target_minutes = to_minutes(*tp)
        real_at_target = target_minutes - offset_minutes
        # Determine day shift and normalize
        day_shift = 0
        if real_at_target < 0:
            real_at_target += 1440
            day_shift = -1
        elif real_at_target >= 1440:
            real_at_target -= 1440
            day_shift = 1
        real_time = f"{real_at_target // 60:02d}:{real_at_target % 60:02d}"
        reference_points.append({
            "wrong_time": target,
            "real_time": real_time,
            "day_shift": day_shift
        })

    explanation = (
        f"The wrong clock is {offset_human} relative to the real clock (status: {clock_status})."
    )

    # Save to DB on successful calculation
    try:
        db_path = get_db_path()
        save_calculation(db_path, real_observed_time, wrong_observed_time,
                         offset_minutes, offset_human, clock_status,
                         target_wrong_times, reference_points)
    except Exception as e:
        if request.is_json:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        else:
            return f"""<!DOCTYPE html>
<html><head><title>Error</title></head>
<body><h1>500 Internal Server Error</h1><p>Could not save calculation.</p></body></html>""", 500, {'Content-Type': 'text/html'}

    # If the request came from a browser form (not JSON), return a simple HTML page
    if not request.is_json:
        # Build a simple HTML response summarizing results
        day_labels = {-1: "previous day", 0: "same day", 1: "next day"}
        table_rows = "".join([
            f"<tr><td>{r['wrong_time']}</td><td>{r['real_time']}</td><td>{day_labels[r['day_shift']]}</td></tr>"
            for r in reference_points
        ])
        # Notification class for status
        if clock_status == "accurate":
            notif_class = "is-success"
        elif clock_status == "fast":
            notif_class = "is-warning"
        else:
            notif_class = "is-danger"
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Broken Clock Results</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
</head>
<body>
  <section class="section">
    <div class="container">
      <div class="box">
        <h1 class="title">Broken Clock Results</h1>
        <div class="notification {notif_class}">
          <strong>Offset:</strong> {offset_human} (the broken clock is <strong>{clock_status}</strong>)
        </div>
        <div class="content">
          <table class="table is-bordered is-fullwidth">
            <tbody>
              <tr><th>Actual time you observed</th><td>{real_observed_time}</td></tr>
              <tr><th>Broken clock showed</th><td>{wrong_observed_time}</td></tr>
              <tr><th>Offset</th><td>{offset_human}</td></tr>
              <tr><th>Clock status</th><td>{clock_status}</td></tr>
            </tbody>
          </table>
        </div>
        <table class="table is-striped is-fullwidth">
          <thead>
            <tr>
              <th>Broken clock shows</th>
              <th>Actual time</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
        <a class="button is-primary" href="/broken-clock">Back</a>
      </div>
    </div>
  </section>
</body>
</html>
"""
        return html, 200, {'Content-Type': 'text/html'}

    # Otherwise return JSON as before
    return jsonify({
        "real_observed_time": real_observed_time,
        "wrong_observed_time": wrong_observed_time,
        "offset_minutes": offset_minutes,
        "offset_human": offset_human,
        "clock_status": clock_status,
        "reference_points": reference_points,
        "explanation": explanation
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
