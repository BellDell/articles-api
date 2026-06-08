# Plan: Simple username/password registration

## 1. Goal

Extend the JWT authentication foundation to support multiple registered users instead of a single env-var user. Add registration routes, persistent user storage (SQLite / DynamoDB), and update login to authenticate against stored users.

## 2. In scope

- New `app/auth/storage.py` — storage facade (follows `app/broken_clock/storage.py` pattern).
  - Delegates to SQLite or DynamoDB based on `STORAGE_BACKEND` env var.
  - Functions: `create_user`, `get_user_by_username`.
  - Defines `DuplicateUserError` domain exception.
  - `create_user` raises `DuplicateUserError` for duplicate usernames only.
  - Routes catch only `DuplicateUserError` for HTTP 409; unexpected exceptions propagate.

- New `app/auth/storage_sqlite.py` — SQLite implementation.
  - Table `auth_users` with columns: `username_canonical TEXT PRIMARY KEY`, `password_hash TEXT`, `created_at TEXT`.
  - Uniqueness enforced by PRIMARY KEY on `username_canonical`.
  - Werkzeug `generate_password_hash` for hashing.
  - Idempotent `ensure_db_initialized`.
  - `sqlite3.IntegrityError` from duplicate insert must be caught and raised as `DuplicateUserError`.
  - `DuplicateUserError` is then mapped to HTTP 409 with body `{"error": "Username already exists"}`.

- New `app/auth/storage_dynamodb.py` — DynamoDB implementation.
  - Reuses the existing shared DynamoDB table.
  - Preserves the existing table key schema: partition key is `app_id`, sort key is `created_at`.
  - Auth user item key:
    - `app_id` = existing application id used by the shared table helper.
    - `created_at` = `"auth_user#<username_canonical>"`.
  - Auth user item attributes include:
    - `entity_type` = `"auth_user"`.
    - `username` = `username_canonical`.
    - `password_hash`.
    - `registered_at`, if an actual creation timestamp is needed.
  - User lookup by username uses `GetItem` with `app_id` and `created_at = "auth_user#<username_canonical>"`.
  - User creation uses `PutItem` with `ConditionExpression` for atomic create-if-not-exists.
  - The `ConditionExpression` must fail if the deterministic key already exists.
  - Conditional `PutItem` failure (`ConditionalCheckFailedException`) must be caught and raised as `DuplicateUserError`.
  - `DuplicateUserError` is then mapped to HTTP 409 with body `{"error": "Username already exists"}`.
  - No table creation at runtime.
  - No `boto3` calls at import time (lazy import).
  - Do not use `Scan`.
  - Do not use `Query` + client-side filtering for username uniqueness.

- New route `GET /auth/register` — returns HTTP 200 with an HTML registration form.
  - Form includes deterministic test markers: `form id="register-form"`, `input name="username"`, `input name="password"`, `input name="confirm_password"`, submit control.

- New route `POST /auth/register` — accepts form data or JSON.
  - On success: HTTP 201, body `{"message": "User registered"}`.
  - Registration does not auto-login the user.
  - Registration does not set the `access_token` cookie.
  - Plaintext password is never stored.
  - Password is stored only as `password_hash`.
  - HTTP route responses must never include `password_hash`.
  - If `username_canonical` already exists: HTTP 409, body `{"error": "Username already exists"}`.
  - If username, password, or confirm_password is missing, empty string, or whitespace-only: HTTP 400, body `{"error": "Username, password, and confirm password are required"}`.
  - If password and confirm_password do not match after required-field validation: HTTP 400, body `{"error": "Passwords do not match"}`.

- Update `POST /auth/login` — authenticate against stored users, with env-var fallback.
  - Existing JWT issuing, cookie behavior, and response shapes unchanged.
  - `POST /auth/login` first canonicalizes username using `username.strip().casefold()`.
  - `POST /auth/login` first checks stored auth users.
  - If a stored user exists, only that stored user's `password_hash` is checked.
  - If a stored user exists and password is wrong, login fails with HTTP 401, body `{"error": "Invalid credentials"}`.
  - Env fallback using `AUTH_USERNAME` / `AUTH_PASSWORD_HASH` is checked only if no stored user exists.
  - If stored user and env-user have the same canonical username, the stored user wins.

- New template `app/templates/auth/register.html` — minimal HTML form.

## 3. Out of scope

- Email, first name, last name fields.
- Password reset, email verification.
- Roles, permissions, OAuth.
- Refresh tokens, CSRF framework.
- Login-required route protection.
- User ownership for Broken Clock or Water Meter records.
- Changing existing Broken Clock or Water Meter routes or storage schemas.
- Terraform, Docker, GitHub Actions, App Runner, IAM, or AWS infrastructure.
- No global auth middleware/enforcement.
- No `app.before_request` blocking behavior.

## 4. Behavior

### Username canonicalization

- `username_canonical = username.strip().casefold()`
- All user storage writes use `username_canonical`.
- All user lookups/login checks use `username_canonical`.
- Username uniqueness is enforced on `username_canonical`.
- Therefore `"Admin"`, `" admin "`, and `"admin"` are the same username.

### Blank / whitespace-only fields

- Empty string or whitespace-only username is treated as missing.
- Empty string or whitespace-only password is treated as missing.
- Empty string or whitespace-only confirm_password is treated as missing.

For missing/blank username, password, or confirm_password:
- HTTP 400
- response body exactly: `{"error": "Username, password, and confirm password are required"}`

### Password mismatch

If password and confirm_password do not match after required-field validation:
- HTTP 400
- response body exactly: `{"error": "Passwords do not match"}`

### Successful registration

- HTTP 201
- response body exactly: `{"message": "User registered"}`
- Registration does not auto-login the user.
- Registration does not set the `access_token` cookie.
- Plaintext password is never stored.
- Password is stored only as `password_hash`.
- HTTP route responses must never include `password_hash`.

### Duplicate username behavior

If `username_canonical` already exists:
- HTTP 409
- response body exactly: `{"error": "Username already exists"}`

This applies to both SQLite and DynamoDB.

### SQLite uniqueness

- SQLite stores users keyed by `username_canonical`.
- SQLite users table must enforce uniqueness using PRIMARY KEY or UNIQUE constraint on `username_canonical`.
- `sqlite3.IntegrityError` from duplicate insert must be caught and translated to:
  - HTTP 409
  - body exactly: `{"error": "Username already exists"}`

### DynamoDB exact key design

- Reuse the existing shared DynamoDB table.
- Preserve the existing table key schema:
  - partition key: `app_id`
  - sort key: `created_at`
- Auth user item key:
  - `app_id` = existing application id used by the shared table helper.
  - `created_at` = `"auth_user#<username_canonical>"`
- Auth user item attributes include:
  - `entity_type` = `"auth_user"`
  - `username` = `username_canonical`
  - `password_hash`
  - `registered_at`, if an actual creation timestamp is needed

### DynamoDB lookup and atomic create

- Do not use `Scan`.
- Do not use `Query` + client-side filtering for username uniqueness.
- User lookup by username must use `GetItem` with:
  - `app_id`
  - `created_at` = `"auth_user#<username_canonical>"`
- User creation must use `PutItem` with `ConditionExpression` for atomic create-if-not-exists.
- The `ConditionExpression` must fail if the deterministic key already exists.
- Conditional `PutItem` failure must be translated to:
  - HTTP 409
  - body exactly: `{"error": "Username already exists"}`
- No table creation at runtime.
- No AWS calls at import time.

### Login precedence

- `POST /auth/login` first canonicalizes username using `username.strip().casefold()`.
- `POST /auth/login` first checks stored auth users.
- If a stored user exists, only that stored user's `password_hash` is checked.
- If a stored user exists and password is wrong, login fails with:
  - HTTP 401
  - body exactly: `{"error": "Invalid credentials"}`
- Env fallback using `AUTH_USERNAME` / `AUTH_PASSWORD_HASH` is checked only if no stored user exists.
- If stored user and env-user have the same canonical username, the stored user wins.

### GET /auth/register

- HTTP 200 with HTML registration form.
- Deterministic test markers: `form id="register-form"`, `input name="username"`, `input name="password"`, `input name="confirm_password"`, submit control.

### Unchanged

- GET /auth/login, POST /auth/logout, GET /auth/me — behavior, response shapes, cookie config all unchanged.
- GET /auth/me never leaks `password_hash`.

## 5. Backward compatibility

- All existing route URLs unchanged.
- Existing auth response shapes outside new/updated routes unchanged.
- Existing Broken Clock, Water Meter, rate limiter behavior unchanged.
- No global auth middleware or `app.before_request` blocking.
- Existing tests must keep passing.

## Registration contract clarifications

### Username canonicalization

* username_canonical = username.strip().casefold()
* All user storage writes use username_canonical.
* All user lookups and login checks use username_canonical.
* Username uniqueness is enforced on username_canonical.
* "Admin", " admin ", and "admin" are the same username.

### Blank field handling

* Empty string or whitespace-only username is treated as missing.
* Empty string or whitespace-only password is treated as missing.
* Empty string or whitespace-only confirm_password is treated as missing.
* Missing or blank username, password, or confirm_password returns HTTP 400 with:
  {"error": "Username, password, and confirm password are required"}

### Password mismatch

* If password and confirm_password do not match after required-field validation, return HTTP 400 with:
  {"error": "Passwords do not match"}

### Successful registration

* Successful registration returns HTTP 201 with:
  {"message": "User registered"}
* Registration does not auto-login the user.
* Successful registration does not set the access_token cookie.
* Plaintext password is never stored.
* Password is stored only as password_hash.
* password_hash must never appear in HTTP route responses.

### Duplicate username

* If username_canonical already exists, `storage.create_user` raises `DuplicateUserError`.
* The route catches `DuplicateUserError` and returns HTTP 409 with:
  {"error": "Username already exists"}
* Unexpected storage errors are not caught; they propagate to Flask default 500 handling.
* This duplicate behavior applies to both SQLite and DynamoDB.

### SQLite uniqueness

* SQLite stores users keyed by username_canonical.
* SQLite users table must enforce uniqueness using PRIMARY KEY or UNIQUE constraint on username_canonical.
* sqlite3.IntegrityError from duplicate insert must be caught and raised as DuplicateUserError.
* DuplicateUserError maps to HTTP 409 with:
  {"error": "Username already exists"}

### DynamoDB key design

* Reuse the existing shared DynamoDB table.
* Preserve the existing table key schema:

  * partition key: app_id
  * sort key: created_at
* Auth user item key:

  * app_id = existing application id used by the shared table helper
  * created_at = "auth_user#<username_canonical>"
* Auth user item attributes include:

  * entity_type = "auth_user"
  * username = username_canonical
  * password_hash
  * registered_at, if an actual creation timestamp is needed

### DynamoDB lookup and atomic create

* Do not use Scan.
* Do not use Query + client-side filtering for username uniqueness.
* User lookup by username must use GetItem with:

  * app_id
  * created_at = "auth_user#<username_canonical>"
* User creation must use PutItem with ConditionExpression for atomic create-if-not-exists.
* The ConditionExpression must fail if the deterministic key already exists.
* Conditional PutItem failure must raise DuplicateUserError.
* DuplicateUserError maps to HTTP 409 with:
  {"error": "Username already exists"}
* No table creation at runtime.
* No AWS calls at import time.

### Login precedence

* POST /auth/login first canonicalizes username using username.strip().casefold().
* POST /auth/login first checks stored auth users.
* If a stored user exists, only that stored user's password_hash is checked.
* If a stored user exists and password is wrong, login fails with HTTP 401 and:
  {"error": "Invalid credentials"}
* Env fallback using AUTH_USERNAME/AUTH_PASSWORD_HASH is checked only if no stored user exists.
* If stored user and env-user have the same canonical username, the stored user wins.

### Required tests

* Test username.strip().casefold() canonicalization.
* Test "Admin", " admin ", and "admin" are treated as the same username.
* Test whitespace-only username/password/confirm_password return the missing-field HTTP 400 response.
* Test successful registration does not set access_token.
* Test successful registration stores password_hash, not plaintext password.
* Test registration, login, and /auth/me responses never include password_hash.
* Test duplicate username returns HTTP 409.
* Test unexpected storage errors (e.g. RuntimeError) are not mapped to HTTP 409.
* Test SQLite duplicate sqlite3.IntegrityError maps to DuplicateUserError / HTTP 409.
* Test DynamoDB GetItem is used for lookup.
* Test DynamoDB PutItem uses ConditionExpression for atomic create.
* Test DynamoDB conditional failure maps to HTTP 409.
* Test stored user login succeeds.
* Test wrong stored-user password fails.
* Test env fallback works only when no stored user exists.
* Test stored user wins over env fallback when usernames conflict.
* Test DynamoDB tests mock/stub boto3 and make no real AWS calls.

## 6. Test strategy

### Route tests

- GET /auth/register loads (200).
- Register page contains `id="register-form"`, username/password/confirm_password inputs.
- `username.strip().casefold()` canonicalization.
- `"Admin"`, `" admin "`, and `"admin"` treated as the same username.
- Successful registration returns 201 and `{"message": "User registered"}`.
- Successful registration does **not** set `access_token` cookie.
- Successful registration stores `password_hash`, not plaintext password.
- Registration/login/me responses never include `password_hash`.
- Duplicate username returns 409 and `{"error": "Username already exists"}`.
- SQLite duplicate `IntegrityError` maps to 409.
- Whitespace-only username/password/confirm_password return the missing-field 400 response.
- Missing or whitespace-only fields return 400 with `{"error": "Username, password, and confirm password are required"}`.
- Password mismatch returns 400 with `{"error": "Passwords do not match"}`.
- Stored user login succeeds.
- Wrong stored-user password fails with 401 and `{"error": "Invalid credentials"}`.
- /auth/me returns `"authenticated": true` after registered-user login.
- Env fallback works only when no stored user exists.
- Stored user wins over env fallback when usernames conflict.

### Storage tests — SQLite

- `create_user` inserts a row; `get_user_by_username` retrieves it.
- `user_exists` returns True/False correctly.
- Password hash is a valid Werkzeug hash.
- Duplicate insert raises `IntegrityError` → maps to 409.

### Storage tests — DynamoDB

- Mock/stub `boto3` — no real AWS calls.
- Test `create_user`, `get_user_by_username`.
- Verify `entity_type = "auth_user"` is set.
- Verify deterministic key: `created_at = "auth_user#<username_canonical>"`.
- Verify lookup uses `GetItem`.
- Verify create uses `PutItem` with `ConditionExpression`.
- Verify conditional failure maps to 409.
- DynamoDB tests mock/stub boto3 and make no real AWS calls.

### Test setup

- `tmp_path` / `monkeypatch` for SQLite paths and environment variables.
- No real AWS calls.

### Run commands

- `python -m pytest -q`
- `python -W error::ResourceWarning -m pytest -q`

## 7. Follow-up steps

- Add route protection in a later PR.
- Add user ownership for feature records in a later PR.
- Consider password policy hardening in a later PR.
