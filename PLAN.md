# Plan: Admin-only user listing page

## 1. Objective

Add an admin-only page (`GET /admin/users`) where users configured through `AUTH_ADMIN_USERS` can view a list of registered application users. Anonymous users and non-admin authenticated users cannot access the page.

## 2. Route

| Method | Route | Endpoint name | Access |
|--------|-------|---------------|--------|
| GET | `/admin/users` | `admin_users` | Admin only |

### 2.1. Access rules

- **Anonymous browser request**: Redirects to `/auth/login` (uses `login_required(mode="html")`).
- **Authenticated non-admin user**: Receives HTTP 403 with `{"error": "Admin access required"}`.
- **Admin user**: Can access the page (HTTP 200, HTML).

### 2.2. Admin check

Use the existing `app.core.authz.is_admin(username)` function, which checks the `AUTH_ADMIN_USERS` env var with canonical username comparison. No separate admin role table is created.

## 3. Data shown

| Field | Source | Notes |
|-------|--------|-------|
| `username_canonical` | Auth storage `auth_users` table / DynamoDB items | The canonical form stored at registration |
| `created_at` | Auth storage | Registration/created timestamp |

### 3.1. Data never shown

- `password_hash` — stripped before rendering
- Password data
- JWT tokens
- Secrets
- Environment variables

## 4. Route handler

Add a new route handler `admin_users` in `app/routes.py`:

```python
def admin_users():
    """GET /admin/users — admin-only user listing page."""
    current = g.get("current_username")
    if not is_admin(current):
        return jsonify({"error": "Admin access required"}), 403
    users = auth_storage.list_users()
    # Strip password_hash before rendering
    for user in users:
        user.pop("password_hash", None)
    return render_template("admin/users.html", users=users), 200
```

### 4.1. Route registration

Add in `register_routes()`:

```python
app.add_url_rule(
    "/admin/users", endpoint="admin_users",
    view_func=admin_users, methods=["GET"],
)
```

### 4.2. Protection strategy

The `/admin/users` route needs two layers of protection:

1. **login_required(mode="html")** — catches anonymous users (redirect to /auth/login).
2. **Admin check inside handler** — returns 403 for non-admin logged-in users.

Wrap the route in `register_routes()`:

```python
ep = "admin_users"
app.view_functions[ep] = login_required(mode="html")(app.view_functions[ep])
```

## 5. Storage: `list_users()` facade

Add a new backend-neutral function to `app/auth/storage.py`:

```python
def list_users():
    """Return a list of user dicts (without password_hash).

    Fields returned: username_canonical, created_at.
    Backend delegates to SQLite or DynamoDB.
    """
    backend = _get_backend()
    if backend == "dynamodb":
        from app.auth.storage_dynamodb import list_users as _fn
        return _fn(None)
    else:
        from app.auth.storage_sqlite import list_users as _fn
        from app.auth.storage_sqlite import get_db_path as _db
        return _fn(_db())
```

### 5.1. SQLite `list_users()`

Add to `app/auth/storage_sqlite.py`:

```python
def list_users(db_path):
    """Return list of user dicts with username_canonical and created_at.

    Does NOT return password_hash. Uses a SELECT that explicitly omits it,
    rather than returning all columns and then stripping.
    """
    ensure_db_initialized(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT username_canonical, created_at FROM auth_users ORDER BY created_at ASC"
        )
        return [dict(row) for row in cursor.fetchall()]
```

### 5.2. DynamoDB `list_users()`

Add to `app/auth/storage_dynamodb.py`:

**Important**: DynamoDB auth users use a deterministic sort key `auth_user#<username_canonical>` but there is no GSI on entity_type. To list all auth users, the implementation must:

1. **Query by app_id** — this returns all items for the app, then filter by `entity_type == "auth_user"` in Python.
2. **Strip password_hash** before returning.

This is an accepted MVP tradeoff: admin-only path uses Query (not Scan) and filters in Python. Document as admin-only and MVP risk.

```python
def list_users(_db_path):
    """Return list of user dicts with username_canonical and created_at.

    Admin-only. Uses Query by app_id + Python filter on entity_type.
    Strips password_hash before returning.
    """
    from app.core.storage.dynamodb import query_all_items
    app_id = _app_id()
    table = _table()
    items = query_all_items(table, "app_id", app_id)
    users = []
    for item in items:
        if item.get("entity_type") != "auth_user":
            continue
        users.append({
            "username_canonical": item["username"],
            "created_at": item.get("registered_at", item["created_at"]),
        })
    return users
```

## 6. Route authorization map update

Update `app/core/authz.py`:

- **PROTECTED_ENDPOINT_MODES**: Add `"admin_users": "html"`.
- **PUBLIC_ENDPOINTS**: No changes (it should NOT be public).

## 7. Template

Create `app/templates/admin/users.html`:

```html
{% extends "broken_clock/_layout.html" %}
{% block title %}Admin - Users{% endblock %}
{% block content %}
<div class="bc-card" style="max-width: 700px;">
  <h1>Registered Users</h1>
  <div class="accent-rule"></div>
  {% if users %}
  <table class="table is-fullwidth">
    <thead>
      <tr>
        <th>Username</th>
        <th>Registered</th>
      </tr>
    </thead>
    <tbody>
      {% for user in users %}
      <tr>
        <td>{{ user.username_canonical }}</td>
        <td>{{ user.created_at }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p>No users registered yet.</p>
  {% endif %}
</div>
{% endblock %}
```

### 7.1. Admin navigation link

Add an "Admin" link in `_layout.html` navbar. Only visible to admin users:

```html
{% if username and is_admin %}
<a class="navbar-item" href="/admin/users">Admin</a>
{% endif %}
```

This requires the context processor to also inject `is_admin`:

```python
@app.context_processor
def inject_username_and_admin():
    return {
        "username": get_current_username(),
        "is_admin": is_admin(get_current_username()) if get_current_username() else False,
    }
```

Update the existing context processor in `register_routes()`.

## 8. Tests required

### 8.1. Route tests (in `tests/test_authorization.py`)

1. Anonymous GET `/admin/users` redirects to `/auth/login` (302).
2. Authenticated non-admin GET `/admin/users` returns 403 with `{"error": "Admin access required"}`.
3. Admin user GET `/admin/users` returns 200.

### 8.2. Authorization map tests (in existing `TestRouteAuthMap`)

4. `admin_users` endpoint is in `PROTECTED_ENDPOINT_MODES`.
5. `admin_users` endpoint is NOT in `PUBLIC_ENDPOINTS`.
6. Route-map test still passes (`test_every_endpoint_is_classified`).

### 8.3. Data tests

7. Admin page lists registered usernames (use `authed_admin_client` fixture).
8. Admin page does NOT include `password_hash` in rendered HTML.
9. Admin page displays `created_at` for each user.

### 8.4. Storage tests

10. SQLite `list_users()` returns users without password hashes.
11. DynamoDB `list_users()` returns users without password hashes.
12. DynamoDB tests mock/stub boto3 and make no real AWS calls.

### 8.5. Backward compatibility

13. All existing auth tests still pass.
14. All existing registration tests still pass.
15. All existing login tests still pass.
16. All existing route authorization tests still pass.
17. All existing ownership tests still pass.

## 9. Files likely to change

| File | Change |
|------|--------|
| `app/core/authz.py` | Add `"admin_users": "html"` to PROTECTED_ENDPOINT_MODES |
| `app/routes.py` | Add `admin_users` handler, register route with login_required, update context processor |
| `app/auth/storage.py` | Add `list_users()` facade function |
| `app/auth/storage_sqlite.py` | Add `list_users()` function |
| `app/auth/storage_dynamodb.py` | Add `list_users()` function |
| `app/templates/admin/users.html` | New file — admin user listing page |
| `app/templates/broken_clock/_layout.html` | Add admin nav link (conditional on admin) |
| `tests/test_authorization.py` | Add admin users route tests, update route-map test, add authed_admin_client fixture |

## 10. Test fixtures

Add to `tests/test_authorization.py`:

```python
@pytest.fixture
def authed_admin_client(client, monkeypatch):
    """Client with registered admin user and AUTH_ADMIN_USERS set."""
    monkeypatch.setenv("AUTH_ADMIN_USERS", "admin_user")
    client.post("/auth/register", json={
        "username": "admin_user",
        "password": "secret123",
        "confirm_password": "secret123",
    })
    client.post("/auth/login", json={
        "username": "admin_user",
        "password": "secret123",
    })
    return client
```

## 11. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| DynamoDB `list_users()` uses Query returning all items + Python filter | Documented as admin-only MVP tradeoff; no sensitive data leaks |
| Admin nav link exposed if `is_admin` template variable leaks | `is_admin` is computed server-side in context processor, not exposed in API |
| `password_hash` accidentally included in template rendering | `list_users()` explicitly omits `password_hash` at the storage level; handler also calls `.pop()` as defense-in-depth |
| Existing route-map test fails if new endpoint not classified | Test `test_every_endpoint_is_classified` enforces classification — will fail immediately |
| Non-admin user sees 403 JSON vs HTML | Route uses `login_required(mode="html")` so non-admin receives 403 in same format as the route content type |

## 12. Open questions

- Should the admin nav link appear in the navbar for admins, or should they navigate manually to `/admin/users`? **Decision**: Add a conditional nav link in `_layout.html` for convenience, only visible to admin users.
- The `list_users()` for DynamoDB uses `query_all_items` which is already used by Broken Clock and Water Meter storage. Is there a risk of mixing item types? **Mitigation**: The function filters by `entity_type == "auth_user"`.
- Should we add `is_admin` to the template context in the existing context processor, or create a separate one? **Decision**: Update the existing context processor to inject `is_admin` alongside `username`.

## 13. Out of scope

- User deletion
- Password reset
- Changing admin users from the UI
- Role management
- Email, profile, avatar, names
- App Runner/IAM changes
- Kubernetes/GitOps changes
- Cloudflare changes
- Database destructive migrations

## 14. Validation commands

```bash
python -m pytest -q
python -W error::ResourceWarning -m pytest -q
```

## 15. Rollback notes

1. Remove `admin_users` from `PROTECTED_ENDPOINT_MODES` in `app/core/authz.py`.
2. Remove `admin_users` route registration from `app/routes.py`.
3. Remove `admin_users` handler from `app/routes.py`.
4. Remove `list_users()` from `app/auth/storage.py`, `storage_sqlite.py`, `storage_dynamodb.py`.
5. Remove `app/templates/admin/users.html`.
6. Remove admin nav link from `_layout.html`.
7. Remove `is_admin` from context processor.
8. Revert test additions.
