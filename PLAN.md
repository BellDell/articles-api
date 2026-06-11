# Plan: Route authorization, username display, and per-user record ownership

## 1. Objective

Add authorization/access control on top of the existing authentication foundation. Anonymous users must be redirected away from protected feature pages, logged-in users must see their username in the UI, and every record must be owned by a user — users see and manage only their own records.

## 2. Public routes

These routes remain accessible to all users (anonymous or authenticated):

| Method | Route | Notes |
|--------|-------|-------|
| GET | `/auth/login` | Login page |
| POST | `/auth/login` | Login action |
| GET | `/auth/register` | Register page |
| POST | `/auth/register` | Register action |
| POST | `/auth/logout` | Logout action |
| GET | `/auth/me` | Auth status (unchanged contract) |
| GET | `/health` | Health check |
| — | `/static/...` | Static files (CSS) |
| GET | `/` | Homepage — keep public. Shows links to Broken Clock and Water Meter, which are individually protected. |

## 3. Protected routes — login_required modes

All Broken Clock and Water Meter routes require authentication. The plan defines two
decorator modes:

- `login_required(mode="html")` — for protected browser/HTML pages.
  Anonymous access redirects to `/auth/login` (HTTP 302).
- `login_required(mode="json")` — for protected API/action/write/delete routes.
  Anonymous access returns HTTP 401 `{"error": "Authentication required"}`.

### 3.1. Broken Clock routes

| Method | Route | Decorator mode | Notes |
|--------|-------|----------------|-------|
| GET | `/broken-clock` | `login_required(mode="html")` | Browser page |
| GET | `/broken-clock/history` | `login_required(mode="html")` | Browser page (default Accept) |
| POST | `/broken-clock/calculate` | `login_required(mode="json")` | API/write action |
| DELETE | `/broken-clock/history/<record_id>` | `login_required(mode="json")` | API/delete action |
| POST | `/broken-clock/history/<record_id>/delete` | `login_required(mode="json")` | Browser delete action |

### 3.2. Water Meter routes

| Method | Route | Decorator mode | Notes |
|--------|-------|----------------|-------|
| GET | `/water-meter` | `login_required(mode="html")` | Browser page |
| GET | `/water-meter/history` | `login_required(mode="html")` | Browser page (default Accept) |
| POST | `/water-meter/readings` | `login_required(mode="json")` | Write action |
| DELETE | `/water-meter/readings/<record_id>` | `login_required(mode="json")` | API/delete action |
| POST | `/water-meter/readings/<record_id>/delete` | `login_required(mode="json")` | Browser delete action |

### 3.3. Routes NOT protected (out of scope)

| Method | Route | Notes |
|--------|-------|-------|
| GET | `/articles` | Articles API — unchanged |
| POST | `/articles` | Articles API — unchanged |
| GET | `/articles/<id>` | Articles API — unchanged |
| GET | `/authors` | Articles API — unchanged |
| GET | `/author/<id>` | Articles API — unchanged |

These are part of the earlier "articles" feature and are not in scope for the auth/ownership model.

## 4. Browser/API unauthorized behavior

### 4.1. `login_required(mode="html")` — Browser (HTML) pages

When an anonymous user accesses a protected route decorated with `mode="html"`:

- Redirect to `/auth/login` with HTTP 302.
- Do not include a `next` query parameter (MVP simplicity).
- This applies to:
  - `GET /broken-clock`
  - `GET /broken-clock/history` (default Accept: text/html)
  - `GET /water-meter`
  - `GET /water-meter/history` (default Accept: text/html)

### 4.2. `login_required(mode="json")` — API / JSON routes

When an anonymous user accesses a protected route decorated with `mode="json"`:

- Return HTTP 401.
- Response body: `{"error": "Authentication required"}`.
- No Set-Cookie header.
- This applies to:
  - `POST /broken-clock/calculate`
  - `DELETE /broken-clock/history/<record_id>`
  - `POST /broken-clock/history/<record_id>/delete`
  - `POST /water-meter/readings`
  - `DELETE /water-meter/readings/<record_id>`
  - `POST /water-meter/readings/<record_id>/delete`
  - Any GET to a protected page with `Accept: application/json`

## 5. Username display requirements

- Every protected HTML page template must show the current username in the navbar.
- Use the canonical username consistently (see §5.3 for canonicalization).
- Show username near a "Logout" button/link.
- No email, full name, avatar, or profile fields required.
- Do not leak `password_hash` or token data in any template.

### 5.1. Template changes

- Modify `app/templates/broken_clock/_layout.html` (the shared navbar):
  - Add `<span>Logged in as <strong>{{ username }}</strong></span>` to the right side of the navbar.
  - Add `<form action="/auth/logout" method="post"><button>Logout</button></form>` adjacent.
  - Wrap these in `{% if username %}` block so anonymous redirects don't see them.

- All protected pages inherit from `_layout.html`, so the username/logout appears everywhere.

### 5.2. Current-user helper using verify_token

`verify_token(token)` returns the **username string** (the `sub` claim) if the token is valid,
or `None` if the token is expired, malformed, or has a bad signature.

Create a safe current-user helper:

```python
def get_current_username(request):
    """Return canonical username from JWT cookie, or None.

    - Returns None for missing/invalid/expired tokens.
    - Returns canonical username for valid tokens.
    - Does not leak token data.
    """
    from app.auth.jwt import verify_token
    from app.core.authz import canonicalize_username
    token = request.cookies.get("access_token")
    if not token:
        return None
    username = verify_token(token)
    if not username:
        return None
    return canonicalize_username(username)
```

This helper is used by `login_required`, the template context processor, and
ownership checks.

### 5.3. Canonical username normalization

```python
def canonicalize_username(value):
    """Normalize a username to canonical form."""
    return value.strip().casefold()
```

This helper is used for:

- Username extracted from JWT/`verify_token`
- `AUTH_ADMIN_USERS` parsing
- `owner_username` writes
- Ownership comparisons
- Admin comparisons
- Tests

### 5.4. Passing username to templates

Create a Flask `@app.context_processor` that adds `username` to all template contexts,
using `get_current_username()` from §5.2. Register this in `register_routes()`.

## 6. Ownership model

Both Broken Clock and Water Meter ownership are in scope for this PR:

- **Broken Clock**: `owner_username` stored on new calculation records. Normal users see only their own calculations. Normal users cannot delete other users' calculations. Legacy ownerless calculations hidden from normal users.
- **Water Meter**: `owner_username` stored on new reading records. Normal users see only their own readings. Normal users cannot delete other users' readings. Legacy ownerless readings hidden from normal users.

### 6.1. New records

When a logged-in user creates a record (Broken Clock calculation or Water Meter reading), the record's `owner_username` is set to the current authenticated canonical username (via `canonicalize_username()`).

### 6.2. Record visibility

- **Normal users**: See only records where `owner_username == current_username`.
- **Admins**: See all records — see §6.4.
- **Legacy records** (NULL or missing `owner_username`): Hidden from normal users; visible only to admins.
- Delete: Same ownership rules apply. Normal users can only delete their own records.

### 6.3. Unauthorized access/delete error response

If a user tries to read or delete a record they do not own (or a record that does not exist):

- **Broken Clock**: HTTP 404 `{"error": "Record not found"}`.
- **Water Meter**: HTTP 404 `{"error": "Reading not found"}`.

Do NOT reveal whether the record exists but belongs to another user.

### 6.4. Admin support

If `AUTH_ADMIN_USERS` is set:

- `AUTH_ADMIN_USERS` is a comma-separated list of canonical usernames (parsed with `canonicalize_username()`).
- Missing/empty `AUTH_ADMIN_USERS` env var → no admins.
- Admins can see and delete all records (including legacy ownerless records) for both Broken Clock and Water Meter.
- Admin all-read for DynamoDB may use Query with just `app_id` (same as current implementation) — accepted MVP risk. Per-user filtering is still applied for normal users.

### 6.5. Enforcement layer

Create a shared authorization helper module `app/core/authz.py`:

```python
def canonicalize_username(value):
    """Normalize a username to canonical form."""
    return value.strip().casefold()


def is_admin(username):
    """Return True if canonical username is in AUTH_ADMIN_USERS."""
    import os
    admins_str = os.environ.get("AUTH_ADMIN_USERS", "")
    if not admins_str.strip():
        return False
    admins = [canonicalize_username(a) for a in admins_str.split(",") if a.strip()]
    return username in admins


def authorize_ownership(record_owner_username, current_username):
    """Return True if current user can access/delete the record."""
    if current_username is None:
        return False
    if record_owner_username is None:
        # Legacy record — only accessible to admins
        return is_admin(current_username)
    if record_owner_username == current_username:
        return True
    return is_admin(current_username)
```

`get_current_username(request)` is defined in §5.2 and uses `canonicalize_username()`.

## 7. SQLite compatibility plan

### 7.1. Idempotent schema migration

Add a helper function to `app/broken_clock/storage_sqlite.py` and `app/water_meter/storage_sqlite.py`:

```python
def _migrate_add_owner_username(conn):
    """Add owner_username column if missing. Idempotent — safe to call repeatedly."""
    cursor = conn.execute("PRAGMA table_info(broken_clock_history)")
    columns = [row[1] for row in cursor.fetchall()]
    if "owner_username" not in columns:
        conn.execute("ALTER TABLE broken_clock_history ADD COLUMN owner_username TEXT")
```

For Water Meter, the table name is `water_meter_readings` instead of `broken_clock_history`.

Call the migration at the end of `ensure_db_initialized`. Old rows get NULL `owner_username`.
NULL `owner_username` rows are legacy records — hidden from normal users.

### 7.2. SQLite tests

- `ensure_db_initialized` adds `owner_username TEXT` column.
- Calling `ensure_db_initialized` again is idempotent (no error on re-migration).
- Owner filtering: `WHERE owner_username = ?` returns correct subset.
- Delete authorization: `DELETE FROM ... WHERE id = ? AND owner_username = ?` works correctly.
- Legacy records (NULL `owner_username`) are hidden from normal users.

## 8. DynamoDB compatibility plan

Deployment context:

- **DynamoDB** is used by App Runner (production AWS).
- **SQLite** is used by k3s/local development.

### 8.1. Save

Add `owner_username` to the Item dict when creating records:

```python
Item={
    ...
    "owner_username": owner_username,
}
```

### 8.2. Get (list) — Normal user

**No Scan for normal-user DynamoDB paths.**

The current implementation uses `query_all_items` with `app_id` as the hash key.
`owner_username` is not the sort key, so Query cannot filter by it directly.

**Normal-user path**: Query by `app_id` (same as current, uses Query — not Scan),
then filter items in Python by `owner_username`. This avoids Scan while still
fetching only the app's partition. This is an accepted MVP trade-off.

**Admin path**: Same as current — Query by `app_id`. Admins see all records.
Admin all-read **may** use Scan as an accepted MVP risk, but Query by `app_id`
is preferred and already implemented.

**Follow-up**: A future PR can add a GSI with PK=`owner_username`, SK=`created_at`
for efficient per-user queries without post-filtering.

### 8.3. Delete

For normal user: Query the item (by `app_id`), check `owner_username` in Python,
then delete only if owned.

For admin: Query + delete without ownership check.

### 8.4. DynamoDB tests

- All DynamoDB tests mock/stub boto3 and make **no real AWS calls**.
- Follow patterns from `tests/test_auth_storage_dynamodb.py` (FakeTable, monkeypatch of `_table()`).
- Tests prove normal-user paths do **not** call Scan.
- New items include `owner_username`.
- Ownership filtering works correctly (User A cannot see/delete User B's records).
- `DynamoDB does not use a file path` remains true.

## 9. Tests

### 9.0. Route authorization matrix (single source of truth)

The implementation **must** define machine-readable constants (preferably Flask endpoint-name based)
that serve as the single source of truth for route authorization. Do not rely only on human-readable
route lists or only on per-route tests — a machine-checkable matrix is required to prevent future
unprotected route drift. Do not implement broad global middleware that accidentally blocks auth
routes, `/health`, or static files.

#### Actual endpoint names from app.url_map

The constants must use the **actual Flask endpoint names** registered by the running app, not
guessed or illustrative names. Before populating `PUBLIC_ENDPOINTS` and `PROTECTED_ENDPOINT_MODES`,
implementers must inspect the real endpoint names from the current `app/routes.py` or `app.url_map`.

If current endpoint names are unclear or inconsistent, implementation must either:

- Use the existing actual endpoint names from `app.url_map`, or
- Explicitly rename route functions only if needed and update tests accordingly.

The example endpoint names listed below are **illustrative only** unless they exactly match
`app.url_map`. The runtime test (§"Runtime route-map test") must fail if a mapped endpoint name
does not exist in `app.url_map`.

#### PUBLIC_ENDPOINTS

A set of Flask endpoint names that are intentionally public. Must include:

- `home` — root/index (PLAN.md §2 says root remains public)
- `health`
- `auth_login_get`, `auth_login_post`
- `auth_register_get`, `auth_register_post`
- `auth_logout`
- `auth_me`
- `static`

Must **not** include any Broken Clock or Water Meter feature endpoint.

#### PROTECTED_ENDPOINT_MODES

A dict mapping every protected Flask endpoint name to exactly one mode string:

- `"html"` — browser page endpoints that redirect anonymous users to `/auth/login`
- `"json"` — API/action/write/delete endpoints that return HTTP 401 `{"error":"Authentication required"}`

Must include all Broken Clock and Water Meter feature endpoints.
The example below is **illustrative** — confirm actual endpoint names from `app.url_map`:

```python
PROTECTED_ENDPOINT_MODES = {
    # Broken Clock
    "broken_clock_form": "html",
    "broken_clock_history": "html",
    "broken_clock_calculate": "json",
    "delete_history": "json",
    "delete_history_html": "json",
    # Water Meter
    "water_meter_form": "html",
    "water_meter_history": "html",
    "water_meter_add_reading": "json",
    "delete_water_meter_reading": "json",
    "delete_water_meter_reading_html": "json",
}
```

Use Flask endpoint names instead of raw URL strings because some routes include path parameters
like `<record_id>`.

#### Runtime route-map test

A dedicated test must derive endpoint sets from `app.url_map`, not only from human-readable
URL tables. The test must iterate `app.url_map` rules, generate requests from actual URL rules
where possible (supplying placeholder record IDs for parameterized routes like `<record_id>`),
and enforce:

- Every mapped endpoint name exists in `app.url_map`.
- Every `app.url_map` endpoint is either in `PUBLIC_ENDPOINTS` or `PROTECTED_ENDPOINT_MODES`.
- No endpoint appears in both maps.
- Every Broken Clock and Water Meter endpoint is in `PROTECTED_ENDPOINT_MODES` (none are public).
- Every protected endpoint has mode `"html"` or `"json"`.
- Protected HTML endpoints redirect anonymous users to `/auth/login`.
- Protected JSON endpoints return HTTP 401 `{"error": "Authentication required"}`.
- Public endpoints remain accessible without auth:
  - login/register pages
  - logout
  - `/auth/me`
  - `/health`
  - static CSS
  - root/index
- Ignore only Flask internal/static endpoint explicitly listed in `PUBLIC_ENDPOINTS`.

The authorization map is the source of truth for endpoint protection, and `app.url_map` tests
prevent future drift.

### 9.1. Authorization redirect tests

- Anonymous GET `/broken-clock` redirects to `/auth/login`.
- Anonymous GET `/broken-clock/history` (Accept text/html) redirects to `/auth/login`.
- Anonymous GET `/water-meter` redirects to `/auth/login`.
- Anonymous GET `/water-meter/history` (Accept text/html) redirects to `/auth/login`.

### 9.2. Authorization JSON/API tests

- Anonymous DELETE `/broken-clock/history/1` returns 401 `{"error": "Authentication required"}`.
- Anonymous POST `/broken-clock/calculate` returns 401 `{"error": "Authentication required"}`.
- Anonymous POST `/water-meter/readings` returns 401 `{"error": "Authentication required"}`.
- Anonymous POST `/water-meter/readings/1/delete` returns 401 `{"error": "Authentication required"}`.
- Anonymous GET `/broken-clock/history` (Accept application/json) returns 401 `{"error": "Authentication required"}`.
- Anonymous GET `/water-meter/history` (Accept application/json) returns 401 `{"error": "Authentication required"}`.

### 9.3. Public route tests (unchanged)

- `GET /auth/login` → 200, HTML.
- `POST /auth/login` → 200 with cookie or 401.
- `GET /auth/register` → 200, HTML.
- `POST /auth/register` → 201.
- `POST /auth/logout` → 200.
- `GET /auth/me` → 200 with contract unchanged.
- `GET /health` → 200 `{"status": "ok"}`.
- `GET /static/css/app.css` → 200.

### 9.4. Authenticated access tests

- Logged-in user GET `/broken-clock` → 200, HTML.
- Logged-in user GET `/broken-clock/history` → 200.
- Logged-in user GET `/water-meter` → 200, HTML.
- Logged-in user shows username in rendered HTML (template contains `{{ username }}`).

### 9.5. Logout session tests

- After logout, protected pages redirect to login again.
- After logout, `/auth/me` returns `{"authenticated": false}`.

### 9.6. Ownership isolation tests

**Broken Clock**:
- User A creates a Broken Clock record → User A sees it.
- User B creates a Broken Clock record → User B sees it.
- User A's history does NOT include User B's records.
- User B's history does NOT include User A's records.
- User A cannot delete User B's Broken Clock records (returns 404 `{"error": "Record not found"}`).

**Water Meter**:
- User A creates a Water Meter reading → User A sees it.
- User B creates a Water Meter reading → User B sees it.
- User A's readings do NOT include User B's readings.
- User B's readings do NOT include User A's readings.
- User A cannot delete User B's Water Meter readings (returns 404 `{"error": "Reading not found"}`).

**Legacy records**:
- Legacy (NULL owner_username) Broken Clock records are hidden from normal users.
- Legacy (NULL owner_username) Water Meter readings are hidden from normal users.
- Legacy records are visible to admin users (if AUTH_ADMIN_USERS is set).

**Admin tests** (if AUTH_ADMIN_USERS is included):
- Admin user can see all records (including legacy and other users').
- Admin user can delete any record.

### 9.7. Username normalization tests

- `canonicalize_username` strips whitespace: `"  Alice  "` → `"alice"`.
- `canonicalize_username` case-folds: `"Alice"` → `"alice"`, `"ALICE"` → `"alice"`.
- `canonicalize_username` handles Unicode casefolding.

### 9.8. verify_token / current-user helper tests

- `verify_token(token)` returns username string for valid token.
- `verify_token(token)` returns `None` for expired token.
- `verify_token(token)` returns `None` for malformed token.
- `verify_token(token)` returns `None` for missing token.
- `get_current_username(request)` returns canonical username for valid token.
- `get_current_username(request)` returns `None` for missing/invalid/expired token.
- `get_current_username(request)` does not leak token data (no JWT payload in output).

### 9.9. SQLite migration tests

- `ensure_db_initialized` adds `owner_username TEXT` column to `broken_clock_history`.
- `ensure_db_initialized` adds `owner_username TEXT` column to `water_meter_readings`.
- Calling `ensure_db_initialized` again is idempotent (no error on re-migration).
- `ALTER TABLE ... ADD COLUMN owner_username TEXT` runs only when column is missing.
- Old rows have NULL `owner_username` after migration (legacy records).

### 9.10. DynamoDB ownership tests

- New DynamoDB items include `owner_username`.
- Normal-user DynamoDB list does **not** call Scan.
- Normal-user DynamoDB list filters by `owner_username` in Python.
- Admin DynamoDB list may use Query (same as current) or Scan only with approval.
- User A cannot see User B's records (DynamoDB mock).
- User A cannot delete User B's records (DynamoDB mock).
- All DynamoDB tests mock/stub boto3 — no real AWS calls.
- Follow patterns from `tests/test_auth_storage_dynamodb.py` (FakeTable, monkeypatch).

### 9.11. Existing test compatibility

- All existing tests in `tests/test_auth.py`, `tests/test_broken_clock_history.py`, `tests/test_broken_clock_delete.py`, `tests/test_water_meter_routes.py`, etc. continue to pass.
- Existing test fixtures that set environment variables continue to work.

## 10. Out of scope

- Password reset.
- Email verification.
- User profile fields (email, full name, avatar).
- External OAuth.
- Large frontend framework or JS rewrite.
- Infrastructure changes (Terraform, Dockerfile, GitHub Actions, App Runner, ECR, IAM).
- Kubernetes/Argo CD changes.
- CSS redesign beyond minimal username/logout visibility.
- Changing auth cookie/JWT semantics.
- Changing `/auth/me` contract.
- `/articles` and `/authors` routes (not protected, no ownership).
- Rate limiter changes.
- Changing registration validation rules.
- Admin user management UI.

## 11. Proposed implementation steps

1. **Create `app/core/authz.py`** — shared authorization helper:
   - `canonicalize_username(value)` — normalizes username via `.strip().casefold()`.
   - `get_current_username(request)` — extracts canonical username from JWT cookie (returns None for invalid/missing).
   - `is_admin(username)` — checks `AUTH_ADMIN_USERS` env var using canonical comparison.
   - `authorize_ownership(record_owner, current_username)` — ownership check with admin support.
   - `login_required(mode="html" | "json")` — decorator that protects routes (redirect or 401).
   - `PUBLIC_ENDPOINTS` — set of endpoint names for intentionally public routes.
   - `PROTECTED_ENDPOINT_MODES` — dict mapping protected endpoint names to "html" or "json".

   **Before populating these constants**, inspect the actual endpoint names from the running app:
   `python -c "from app.app import app; [print(r.endpoint) for r in app.url_map.iter_rules()]"`.
   The example names in §9.0 are illustrative; only confirmed `app.url_map` names must be used.
   Articles-related endpoints (`get_authors`, `get_articles`, `get_author`, `get_article`) are
   out of scope and should also be listed in `PUBLIC_ENDPOINTS` (they are public, not protected).

2. **Add context processor** in `app/routes.py`:
   - Inject `username` into all template contexts using `get_current_username()`.

3. **Apply `login_required` to protected routes** in `app/routes.py`:
   - Each route gets the correct mode per §3.1 and §3.2.
   - Not applied to public routes.

4. **Update SQLite storage** for Broken Clock and Water Meter:
   - Add idempotent `_migrate_add_owner_username()` in `ensure_db_initialized`.
   - Extend `save_calculation` / `save_reading` with `owner_username` parameter.
   - Extend `get_history` / `get_readings` with `owner_username` filter (`WHERE owner_username = ?`).
   - Extend delete functions with `owner_username` filter (`DELETE ... WHERE id = ? AND owner_username = ?`).

5. **Update DynamoDB storage** for Broken Clock and Water Meter:
   - Add `owner_username` to Item on save.
   - For normal-user list: Query by `app_id` + filter in Python by `owner_username` (no Scan).
   - For delete: fetch item, verify ownership, then delete.
   - Admin: same as current (Query all, no filter).

6. **Update storage facades** (`app/broken_clock/storage.py`, `app/water_meter/storage.py`):
   - Pass `owner_username` through facade to backend.
   - Add `owner_username` parameters to facade functions.

7. **Update templates** for username display:
   - `app/templates/broken_clock/_layout.html`: add `{{ username }}` display and logout button in navbar.

8. **Write tests** — see §9 for full list.

## 12. Manual verification commands

```bash
# Run all tests
python -m pytest -q

# Run with ResourceWarning detection
python -W error::ResourceWarning -m pytest -q

# Start the app
python -m app.app

# Verify health endpoint
curl http://localhost:5000/health

# Verify public pages
curl -s http://localhost:5000/auth/login | head -20
curl -s http://localhost:5000/auth/register | head -20

# Verify protected page redirect (anonymous)
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5000/broken-clock
# Should return 302

# Verify protected page redirect (anonymous, with browser Accept header)
curl -s -o /dev/null -w '%{http_code}\n' -H "Accept: text/html" http://localhost:5000/broken-clock
# Should return 302

# Verify protected API returns 401 (anonymous)
curl -s -o /dev/null -w '%{http_code}\n' -H "Accept: application/json" http://localhost:5000/broken-clock
# Should return 401

# Register a user
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"secret123","confirm_password":"secret123"}'

# Login and capture cookie
curl -c /tmp/cookies.txt -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"secret123"}'

# Verify protected page accessible with cookie
curl -b /tmp/cookies.txt http://localhost:5000/broken-clock

# Verify history shows user's records
curl -b /tmp/cookies.txt -H "Accept: application/json" http://localhost:5000/broken-clock/history

# Verify logout clears session
curl -c /tmp/cookies.txt -X POST http://localhost:5000/auth/logout
curl -b /tmp/cookies.txt http://localhost:5000/broken-clock
# Should redirect to login

# Verify ownership isolation
curl -b /tmp/cookies.txt http://localhost:5000/broken-clock/history/1
# Should return 404 if record belongs to another user
```

## 13. Rollback notes

If authorization causes issues:

1. Revert `app/core/authz.py` — remove helper module.
2. Revert `app/routes.py` — remove `login_required` decorator from routes, remove context processor.
3. Revert all storage files — remove `owner_username` from save/get/delete signatures.
4. Revert schema migrations — remove `ALTER TABLE ADD COLUMN owner_username` from `ensure_db_initialized`.
5. Revert `_layout.html` — remove username display and logout button.
6. No database rollback needed: SQLite `ALTER TABLE ADD COLUMN` is additive; existing apps continue to work without reading the column. DynamoDB items with `owner_username` continue to work with old code (extra attribute is ignored).
7. Existing tests serve as regression guard — they must all pass before and after each step.
