# Plan: Add home page at GET /

## 1. Goal

Add a simple home page at `GET /` with links to the Broken Clock Calculator and its history, making the root URL useful instead of returning 404.

## 2. In scope

- Add `GET /` route mapped to a new handler.
- Create `app/templates/broken_clock/home.html` template.
- Add a "Home" link to the existing navbar in `_layout.html`, active when on the home page.
- Wire the new route via `register_routes` in `app/routes.py`.

## 3. Out of scope

- No storage or database changes.
- No DynamoDB changes.
- No delete history or other new features.
- No auth or user_id.
- No changes to existing route URLs (`/broken-clock`, `/broken-clock/calculate`, `/broken-clock/history`).
- No JSON API changes.
- No Terraform, GitHub Actions, or Docker changes.
- No changes to existing templates (`form.html`, `result.html`, `history.html`, `error.html`).

## 4. Template and navigation changes

### New template: `app/templates/broken_clock/home.html`

- Extends `_layout.html`.
- Title: "Home" or "Broken Clock App".
- Content: a brief welcome heading and two buttons or cards linking to:
  - `/broken-clock` — "Calculator"
  - `/broken-clock/history` — "History"
- Simple Bulma styling consistent with existing pages.

### Navigation update: `app/templates/broken_clock/_layout.html`

- Add a "Home" navbar link pointing to `/`.
- The link should accept the same `nav_active_home` pattern used by Calculator and History links (via a template variable or block).

## 5. Test strategy

- Existing tests continue to pass.
- Add tests (in a new or existing test file):
  - `test_home_page_returns_200` — `GET /` returns 200.
  - `test_home_page_contains_calculator_link` — page contains a link or text pointing to `/broken-clock`.
  - `test_home_page_contains_history_link` — page contains a link or text pointing to `/broken-clock/history`.
- Keep HTML assertions simple — check for important text/links, not exact structure.

## 6. Follow-up steps

- None immediately; the home page is a small standalone addition.
- If more pages are added later, the home page can be expanded with a dashboard or index of available tools.
