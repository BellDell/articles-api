# Plan: Water Meter meter name suggestions

## 1. Goal

Improve the Water Meter form by suggesting existing meter names via an HTML `<datalist>` while still allowing the user to type a new name. The suggestions are loaded from stored data (SQLite or DynamoDB).

## 2. UX behavior

- The meter name input uses an HTML `<input>` with an associated `<datalist>` element.
- The datalist is populated with distinct `meter_name` values from existing readings.
- The user can pick a name from the suggestions or type a new one.
- If the field is left blank, it still defaults to `"main"` on submission (unchanged).
- The input `name` attribute remains `meter_name` so POST handling is unchanged.

## 3. In scope

- Add `get_meter_names()` to the Water Meter storage facade.
- **No new JSON endpoint** — meter names are rendered into the HTML template only.
- Existing JSON response shapes unchanged.
- Existing POST /water-meter/readings behavior unchanged.
- Add SQLite implementation: query distinct `meter_name` values from `water_meter_readings`.
- Add DynamoDB implementation: query items for `app_id`, filter `entity_type="water_meter"`, collect distinct `meter_name` values.
- Update `GET /water-meter` route to pass meter names to the template.
- Update the form template to render an `<input>` with `<datalist>`.
- Add tests for storage (both SQLite and DynamoDB), route, and template.

## 4. Out of scope

- No delete or edit readings.
- No storage schema changes.
- No DynamoDB key schema changes.
- No Terraform, Docker, or GitHub Actions changes.
- No auth, charts, or user_id.
- No changes to Broken Clock behavior.

## 5. Storage responsibilities

### Facade (`app/water_meter/storage.py`)

- Add `get_meter_names(db_path)` dispatching by `STORAGE_BACKEND`.

### SQLite (`app/water_meter/storage_sqlite.py`)

- Query: `SELECT DISTINCT meter_name FROM water_meter_readings ORDER BY meter_name`.
- Return a list of strings.

### DynamoDB (`app/water_meter/storage_dynamodb.py`)

- Use **Query** by `app_id` (the DynamoDB partition key) — never Scan.
- Filter items where `entity_type="water_meter"` client-side after Query.
- Collect distinct `meter_name` values and return them sorted alphabetically.
- Do not change the existing key schema (`app_id` partition key, `created_at` sort key).
- Do not add a GSI or Terraform change.

## 6. Route/template behavior

- `GET /water-meter` calls `get_meter_names(db_path)`.
- Passes a list named `meter_names` to the template — does not overwrite `meter_name`.
- Form template renders an `<input name="meter_name">` with `list="meter-name-options"` attribute.
- The datalist element uses `id="meter-name-options"` — separate from the input name.
- The `name` attribute remains `meter_name` — POST handling unchanged.
- Existing error-param behavior for meter_name is preserved.
- The user can type a new meter name not present in the datalist — no restriction to existing values.

## 7. Test strategy

- All existing 92 tests pass unchanged.
- New storage tests:
  - SQLite: `get_meter_names` returns distinct names; returns empty list when no readings.
  - DynamoDB: returns names only from `entity_type="water_meter"` items; ignores broken_clock items.
- New route tests:
  - GET /water-meter passes meter names to template.
  - Template renders a `<datalist>` element.
  - Existing POST behavior unchanged.
- DynamoDB tests use mocked boto3 — no real AWS calls.
- All tests use `tmp_path` + `monkeypatch` for DB isolation.

## 8. Follow-up steps

- None — this is a small isolated UX improvement.
