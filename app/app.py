from flask import Flask, request, jsonify
import os
import sys
from datetime import datetime

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


@app.route("/articles")
def get_articles():
    articles_with_authors = []
    for article in DATA["articles"]:
        article_copy = article.copy()
        article_copy["author"] = find_author(article_copy["author_id"]) 
        article_copy.pop("author_id", None)
        articles_with_authors.append(article_copy)
    return jsonify(articles_with_authors)


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
        <p class="subtitle">Enter what the broken clock shows now. The real observed time defaults to your current system time.</p>
        <form action="/broken-clock/calculate" method="post">
          <div class="field">
            <label class="label">Real observed time (HH:MM)</label>
            <div class="control">
              <input class="input" type="text" name="real_observed_time" value="{default_real}" placeholder="HH:MM">
            </div>
          </div>
          <div class="field">
            <label class="label">Wrong observed time (HH:MM)</label>
            <div class="control">
              <input class="input" type="text" name="wrong_observed_time" value="10:00" placeholder="HH:MM">
            </div>
          </div>
          <div class="field">
            <label class="label">Target wrong times (comma-separated HH:MM)</label>
            <div class="control">
              <input class="input" type="text" name="target_wrong_times" value="00:00,07:00,09:00" placeholder="00:00,07:00,09:00">
            </div>
          </div>
          <div class="field">
            <div class="control">
              <button class="button is-primary" type="submit">Calculate</button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </section>
</body>
</html>
"""


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
        return jsonify({"error": "Request must be JSON or form data"}), 400

    # Required field: wrong_observed_time
    if "wrong_observed_time" not in data or not str(data.get("wrong_observed_time")).strip():
        return jsonify({"error": "Missing required field: wrong_observed_time"}), 400

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
        return jsonify({"error": "All times must be in valid HH:MM format (24-hour)"}), 400

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
            return jsonify({"error": f"Invalid target time: {target}"}), 400
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
              <tr><th>Real observed time</th><td>{real_observed_time}</td></tr>
              <tr><th>Wrong observed time</th><td>{wrong_observed_time}</td></tr>
              <tr><th>Offset</th><td>{offset_human}</td></tr>
              <tr><th>Clock status</th><td>{clock_status}</td></tr>
            </tbody>
          </table>
        </div>
        <table class="table is-striped is-fullwidth">
          <thead>
            <tr>
              <th>Broken clock shows</th>
              <th>Real time</th>
              <th>Day</th>
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
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
