# Plan: Water Meter reading date input UX

## 1. Goal

Improve the Water Meter reading date field by switching to a browser-native `<input type="date">` and defaulting to today's date on the form page.

## 2. In scope

- Change the date input in `app/templates/water_meter/form.html` from `type="text"` to `type="date"`.
- Keep the field `name="reading_date"` unchanged.
- Pass a `default_date` template variable from the route handler (`GET /water-meter`) set to today's date in `YYYY-MM-DD` format.
- Use the default as the input's `value` when no error-preserved value is present.
- When an error redirect returns query params, the previously submitted date takes precedence (current behavior).
- Update `test_water_meter_routes.py` or `test_water_meter_domain.py` only if tests fail.
- Existing validation still expects `YYYY-MM-DD` — the browser always submits this format from `type="date"`.

## 3. Out of scope

- No JavaScript date picker library (browser-native only).
- No storage changes.
- No route URL changes (still `GET /water-meter`).
- No JSON response shape changes.
- No DynamoDB or SQLite changes.
- No Terraform, Docker, or GitHub Actions.
- No timezone or user locale handling.
- No edit/delete/charts.

## 4. UI behavior

- Text input renders a browser-native date picker on supporting browsers.
- On desktop browsers without date picker support, a plain text input appears (graceful degradation).
- The default date is today in `YYYY-MM-DD` format.
- If the user navigated back via a validation error with query params, the submitted date is used instead of today's default.
- Manual `YYYY-MM-DD` entry still works.

## 5. Test strategy

- All 92 existing tests pass.
- Two tests may need small updates:
  - `test_form_returns_200` — verify the response text contains today's date or does not break.
  - A new or updated test verifying `type="date"` attribute is present in the rendered HTML (optional — avoids brittle HTML assertions).
- No test changes strictly required — all existing route tests use form POST, which is unchanged.

## 6. Compatibility rules

- Route URL unchanged: `GET /water-meter`.
- Form `action` unchanged: `/water-meter/readings`.
- Form field `name` unchanged: `reading_date`.
- Validation unchanged: `YYYY-MM-DD`.
- POST handler unchanged: reads `reading_date` from form data.
- Error redirect unchanged: preserves submitted value via query param.
