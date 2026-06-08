# Plan: JWT authentication foundation

## 1. Goal

Add a small authentication foundation for the Flask app using JWT access tokens stored in an HttpOnly cookie.

## 2. In scope

- New `app/auth/` package with JWT helper functions for issuing and verifying access tokens.
- Login, logout, and current-user routes added to the existing centralized `app/routes.py`.
- `GET /auth/login` — renders an HTML login page (no auth required to view).
- `POST /auth/login` — accepts credentials, returns JSON + sets cookie.
- `POST /auth/logout` — clears cookie, returns JSON.
- `GET /auth/me` — always returns 200 with authentication status.
- Password verification using Werkzeug `check_password_hash`.
- Environment variables:
  - `AUTH_USERNAME` — the single allowed username.
  - `AUTH_PASSWORD_HASH` — a Werkzeug-generated bcrypt hash of the password.
  - `JWT_SECRET_KEY` — secret used to sign and verify JWT tokens.
  - `AUTH_COOKIE_SECURE` — toggles the Secure flag on the auth cookie.
- Cookie behavior:
  - HttpOnly flag set.
  - SameSite=Lax.
  - Secure flag controlled by `AUTH_COOKIE_SECURE` only.
- Add `PyJWT` to `requirements.txt` if not already present.
- Tests covering all auth behaviors deterministically.

## 3. Out of scope

- User registration.
- Password reset.
- Refresh tokens.
- Roles/permissions.
- OAuth/social login.
- CSRF framework integration.
- Global auth middleware, `app.before_request` enforcement, or redirect-to-login.
- Protecting existing Broken Clock or Water Meter routes.
- Adding `user_id` to existing Broken Clock or Water Meter records.
- Changing existing route URLs.
- Changing existing JSON response shapes outside new auth routes.
- Changing existing storage schemas for Broken Clock, Water Meter, or rate limiter.
- Terraform, Docker, GitHub Actions, App Runner, IAM, or AWS infrastructure changes.
- Flask-JWT-Extended or other auth frameworks.
- Broad dependency upgrades.

## 4. Behavior

### Routes

#### `GET /auth/login`

- Returns HTTP 200 with a small HTML login page.
- The HTML includes deterministic test markers:
  - A `<form id="login-form">` element.
  - An `<input name="username">` element.
  - An `<input name="password">` element.
  - A submit button or submit input.
- No authentication required to view.

#### `POST /auth/login`

- Accepts JSON body: `{"username": "...", "password": "..."}`.
- On success (matching `AUTH_USERNAME` and verified against `AUTH_PASSWORD_HASH`):
  - Sets an HttpOnly cookie named `access_token` containing a signed JWT.
  - Returns HTTP 200 with body `{"message": "Login successful"}`.
- On failure (unknown username or wrong password):
  - Returns HTTP 401 with body `{"error": "Invalid credentials"}`.
  - Does not set the cookie.

#### `POST /auth/logout`

- Clears the `access_token` cookie by setting an empty value with immediate expiry.
- Returns HTTP 200 with body `{"message": "Logged out"}`.

#### `GET /auth/me`

- Always returns HTTP 200.
- If a valid, non-expired `access_token` cookie is present:
  - Body: `{"authenticated": true, "username": "<username from token>"}`
- If the cookie is missing, invalid, expired, or malformed:
  - Body: `{"authenticated": false}`
- Never returns 401.

### JWT token

- Signed with HS256 using `JWT_SECRET_KEY`.
- Contains claims: `sub` (username), `iat` (issued at), `exp` (expiration).
- Default expiration: 24 hours from issuance.

### Cookie configuration

- Cookie name: `access_token`.
- `HttpOnly=True` always.
- `SameSite=Lax` always.
- `Secure` flag:
  - `True` when `AUTH_COOKIE_SECURE` is "true", "1", "yes", or "on" (case-insensitive).
  - `False` when `AUTH_COOKIE_SECURE` is "false", "0", "no", or "off" (case-insensitive).
  - `False` when `AUTH_COOKIE_SECURE` is unset or empty (default for local/MVP).

### AUTH_COOKIE_SECURE accepted values

| Value (case-insensitive) | Secure flag |
|---|---|
| "true", "1", "yes", "on" | True |
| "false", "0", "no", "off" | False |
| Missing / empty | False |

### Password verification

- Werkzeug's `check_password_hash(password, AUTH_PASSWORD_HASH)` is used.
- `AUTH_USERNAME` is compared case-sensitively.

### Dependencies

- `PyJWT` — the only new direct dependency.
- Werkzeug password utilities are already available via Flask's dependency chain. No separate dependency declaration needed unless the project convention requires listing direct imports explicitly.

## 5. Backward compatibility

- Existing route URLs remain unchanged.
- Existing Broken Clock behavior remains unchanged.
- Existing Water Meter behavior remains unchanged.
- Existing rate limiter behavior remains unchanged.
- No global auth middleware intercepts or blocks any existing route.
- Existing tests must keep passing.
- No AWS calls at import time.
- Tests must not make real AWS calls.

## 6. Test strategy

### Deterministic expired token tests

- The JWT helper accepts an optional `expires_in` parameter (or similar) for token issuance.
- Tests create an explicitly expired token by passing a delta of zero or negative seconds.
- No sleeping or real waiting in tests.

### Unit tests — JWT helpers

- `issue_token(username)` returns a string JWT.
- `verify_token(token)` returns the username for a valid token.
- `verify_token(token)` returns `None` for an expired token (created deterministically via test helper).
- `verify_token(token)` returns `None` for a tampered / bad-signature token.

### Route tests — `POST /auth/login`

- Valid credentials → status 200, body `{"message": "Login successful"}`, response has `Set-Cookie` header containing `access_token`.
- Invalid username → status 401, body `{"error": "Invalid credentials"}`.
- Invalid password → status 401, body `{"error": "Invalid credentials"}`.
- Missing body fields → appropriate 400-level error.

### Route tests — `POST /auth/logout`

- Response status 200, body `{"message": "Logged out"}`, cookie cleared (empty value, past expiry).

### Route tests — `GET /auth/me`

- Authenticated (valid cookie) → status 200, body `{"authenticated": true, "username": "<username>"}`.
- Anonymous (no cookie) → status 200, body `{"authenticated": false}`.
- Expired token cookie → status 200, body `{"authenticated": false}`.
- Invalid/tampered token cookie → status 200, body `{"authenticated": false}`.

### Route tests — `GET /auth/login`

- Status 200, response is HTML containing username input, password input, and submit action.

### Cookie tests

- Assert the cookie name is `access_token`.
- Assert `HttpOnly` attribute is present.
- Assert `SameSite=Lax` attribute is present.
- Set `AUTH_COOKIE_SECURE=false` and assert `Secure` is absent from the cookie.
- Set `AUTH_COOKIE_SECURE=true` and assert `Secure` is present.

### Test setup

- `monkeypatch` to set `AUTH_USERNAME`, `AUTH_PASSWORD_HASH`, `JWT_SECRET_KEY`, and `AUTH_COOKIE_SECURE`.
- No real production secrets.
- No AWS calls.

### Run commands

- `python -m pytest -q`
- `python -W error::ResourceWarning -m pytest -q`

## 7. Follow-up steps

- Protect existing Broken Clock and Water Meter routes behind authentication.
- Add role-based access or multi-user support.
- Add refresh token rotation.
- Add CSRF protection for cookie-based auth.
- Transition to OAuth2 / social login if needed.
