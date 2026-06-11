# Plan: Auth UI polish, shared CSS, and quiet health logs

## 1. Objective

Improve authentication page appearance and browser behavior, extract shared CSS, and suppress noisy health-check log lines. Keep this PR small and safe — no route protection, no ownership changes, no backend storage changes.

## 2. In scope

- Create `app/static/css/app.css` with shared styling:
  - Base typography, colors, layout.
  - Centered card layout for auth pages.
  - Readable form labels, clear error/success messages.
  - Accessible focus states.
  - Mobile-friendly width.
  - No external CSS/CDN dependencies.
  - No build tools.

- Update templates to use the shared CSS:
  - Base layout template includes `<link rel="stylesheet" href="...">` to `app.css`.
  - Remove large inline style blocks where possible.
  - Move auth-page-specific styles into `app.css`.

- Improve `/auth/login` page visually:
  - Centered card with form fields.
  - Clear error display on invalid credentials.
  - Link to `/auth/register` for new users.

- Improve `/auth/register` page visually:
  - Centered card with form fields.
  - Clear error display on validation failures.
  - On success, redirect browser to `/auth/login` with a flash/success message.
  - Link to `/auth/login` for existing users.

- Improve browser form behavior for auth routes:
  - Browser `POST /auth/register` on success redirects to `/auth/login` (or renders success message and link).
  - Browser `POST /auth/register` on validation error re-renders with error message.
  - Browser `POST /auth/login` on success redirects to `/` (or a safe next URL).
  - Browser `POST /auth/login` on invalid credentials re-renders with error message.
  - Browser `POST /auth/logout` redirects to `/auth/login` with confirmation.
  - API-style requests (no `Accept: text/html`) preserve existing JSON response shapes.

- Suppress noisy successful `/health` access logs:
  - Filter out `GET /health 200` lines from the werkzeug access log.
  - Do not hide real application errors or tracebacks.
  - Do not change `/health` response body or status code.
  - Safe for both App Runner and k3s.

## 3. Out of scope

- `login_required` route protection.
- Water Meter ownership or admin behavior.
- Broken Clock ownership.
- IAM/App Runner/CloudFormation changes.
- Kubernetes/Argo CD changes.
- DynamoDB schema redesign.
- Password reset or email verification.
- Large frontend framework or JS rewrite.
- Changing auth storage, JWT, or cookie behavior.
- Changing registration validation rules.
- Changing `/auth/me` contract.
- Changing Broken Clock or Water Meter business logic.

## 4. Current behavior to preserve

- All auth route URLs unchanged:
  - `GET /auth/login`, `POST /auth/login`, `GET /auth/register`, `POST /auth/register`, `POST /auth/logout`, `GET /auth/me`.
- API-style requests (JSON Accept header or `is_json` requests) continue to return:
  - Successful registration: `HTTP 201 {"message": "User registered"}`.
  - Duplicate username: `HTTP 409 {"error": "Username already exists"}`.
  - Successful login: `HTTP 200 {"message": "Login successful"}` + cookie.
  - Invalid login: `HTTP 401 {"error": "Invalid credentials"}`.
  - Registration validation errors: `HTTP 400` with existing error body.
- `/health` continues to return `HTTP 200 {"status": "ok"}`.
- `/auth/me` continues to return existing contract:
  - Authenticated: `{"authenticated": true, "username": "..."}`.
  - Anonymous: `{"authenticated": false}`.
- No cookie flag changes.
- No registration validation rule changes.
- No duplicate-user behavior changes.
- No route protection changes.
- No Water Meter or Broken Clock changes.
- Existing rate limiter behavior unchanged.

## 5. Proposed implementation steps

1. Create `app/static/css/app.css`:
   - CSS custom properties for colors/spacing/radii.
   - Card layout (`.auth-card`) for centering auth forms.
   - Form styling (`.auth-form`): labels, inputs, buttons.
   - Error/success message styling (`.message-error`, `.message-success`).
   - Responsive width using `max-width` and `margin: 0 auto`.
   - Accessible focus outlines.

2. Update base layout template (`app/templates/base.html` or similar):
   - Add `<link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">`.
   - Ensure existing page structure is not broken.

3. Update `app/templates/auth/login.html`:
   - Use `auth-card` and `auth-form` CSS classes.
   - Replace large inline style blocks.
   - Add error message display region.
   - Add link to `/auth/register`.

4. Update `app/templates/auth/register.html`:
   - Use `auth-card` and `auth-form` CSS classes.
   - Replace large inline style blocks.
   - Add error message display region.
   - Add link to `/auth/login`.
   - On success redirect or render success message.

5. Update route handlers in `app/routes.py` (auth login/register):
   - Distinguish browser vs API requests using `Accept` header or `request.is_json`.
   - For browser requests:
     - `POST /auth/register` success → redirect `/auth/login?registered=1`.
     - `POST /auth/register` error → re-render register page with error.
     - `POST /auth/login` success → redirect `/`.
     - `POST /auth/login` error → re-render login page with error.
     - `POST /auth/logout` → redirect `/auth/login`.
   - For API requests (JSON content type or `Accept: application/json`):
     - Keep existing JSON response shapes unchanged.

6. Add health log filter:
   - Create a small werkzeug log filter in `app/app.py` or `app/core/logging.py` that drops `GET /health 200` records from the access logger.
   - Ensure it does not suppress non-200 `/health` responses or other routes.
   - Ensure it does not suppress tracebacks or error logs.

7. Verify all existing tests still pass before any new tests.

## 6. Browser/API response mode strategy

Use `request.is_json` (checking `Content-Type` or `Accept` header) to distinguish:

- **Browser flow**: Form `POST` typically sends `Content-Type: application/x-www-form-urlencoded` and `Accept: text/html`. `request.is_json` returns `False` or the `Accept` header includes `text/html`. Use `request.accept_mimetypes.best_match` to prefer HTML.
  - Redirect on success.
  - Re-render with error on failure.

- **API flow**: JSON requests with `Content-Type: application/json` or `Accept: application/json`. `request.is_json` returns `True`.
  - Return existing JSON responses unchanged.

- **Accept header preference**: `request.accept_mimetypes.best_match(["text/html", "application/json"])`.
  - If `text/html` is preferred → browser mode.
  - If `application/json` is preferred → API mode.
  - Default to API mode for backward compatibility with existing tests that post form data without explicit Accept headers.

- This approach matches existing patterns in the codebase (see `broken_clock_history`, `water_meter_history` which already use Accept header detection).

## 7. Health log suppression strategy

- The app runs on Flask/waitress/werkzeug which prints access log lines like:
  `INFO:werkzeug:127.0.0.1 - - [date] "GET /health HTTP/1.1" 200 -`
- Create a `HealthLogFilter(logging.Filter)` that:
  - Attaches to the `werkzeug` logger.
  - In `filter(record)`, checks if the log message contains `"GET /health"` and `"200"`.
  - Returns `False` to drop the record if it matches, `True` otherwise.
- Register the filter in `app/app.py` after the app is created.
- The filter does not affect error responses (non-200) or other routes.
- The filter does not affect Python tracebacks or application error logs.
- The `/health` endpoint itself continues to work as before.

## 8. Tests

Add/update tests for:

- `GET /auth/login` renders HTML and links to shared CSS (`app.css` or `css/app.css`).
- `GET /auth/register` renders HTML and links to shared CSS.
- Browser-style successful registration redirects to `/auth/login` (HTTP 302 or 303).
- Browser-style registration validation error renders HTML with an error message.
- API-style successful registration still returns `HTTP 201 {"message": "User registered"}`.
- API-style duplicate registration still returns `HTTP 409 {"error": "Username already exists"}`.
- Browser-style successful login redirects to `/` (HTTP 302 or 303) and sets cookie.
- API-style successful login still returns `HTTP 200 {"message": "Login successful"}`.
- Browser-style invalid login renders HTML with an error message.
- Browser logout redirects to `/auth/login`.
- `/auth/me` behavior unchanged (both authenticated and anonymous).
- `/health` returns `HTTP 200 {"status": "ok"}`.
- Health log filter drops `GET /health 200` lines but does not suppress non-200 health responses or other routes.
- No real AWS calls in tests.

## 9. Rollback notes

If the auth UI changes cause issues:

- Revert `app/routes.py` changes to `auth_login_post`, `auth_register_post`, `auth_logout` — restore the pure JSON/form handlers.
- Revert template changes — restore old inline styles.
- Revert `app/app.py` changes — remove the health log filter.
- Remove `app/static/css/app.css` if it was added.
- All changes are in Python/HTML/CSS files only — no database or infrastructure changes.
- Existing tests serve as regression guard.

## 10. Manual verification commands

```bash
# Run all tests
python -m pytest -q

# Run with ResourceWarning detection
python -W error::ResourceWarning -m pytest -q

# Start the app
python run.py

# Verify health endpoint
curl http://localhost:5000/health

# Verify health logs are quiet (should see no "GET /health 200" lines)

# Verify browser login page
open http://localhost:5000/auth/login

# Verify browser register page
open http://localhost:5000/auth/register

# Test API-style registration
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"secret123","confirm_password":"secret123"}'

# Test API-style login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"secret123"}'

# Test API-style duplicate registration
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"secret123","confirm_password":"secret123"}'
```
