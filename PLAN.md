# Plan: Delete individual Water Meter readings

## 1. Goal

Add the ability to delete individual Water Meter reading records from both SQLite and DynamoDB backends. Records can be removed via a JSON API or an HTML form POST on the history page.

## 2. In scope

- Add `delete_reading(record_id)` to the storage facade.
- Add SQLite implementation (delete by id, return True/False).
- Add DynamoDB implementation (query by app_id, filter entity_type="water_meter", find matching id, delete by app_id + created_at, return True/False).
- Add `DELETE /water-meter/readings/<record_id>` JSON route.
- Add `POST /water-meter/readings/<record_id>/delete` HTML fallback route.
- Add a delete button per row on the Water Meter history page.
- Add tests for storage (SQLite and DynamoDB) and routes (JSON and HTML).

## 3. Out of scope

- No bulk delete or delete-all.
- No edit readings.
- No auth or CSRF implementation.
- No storage schema changes.
- No DynamoDB key schema changes.
- No Terraform, App Runner, Docker, or GitHub Actions changes.
- No changes to Broken Clock behavior.

## 4. Route / API behavior

### JSON route: `DELETE /water-meter/readings/<record_id>`

- Deletes the record with the given id.
- Returns `{"deleted": True, "id": <id>}` with status 200 on success.
- Returns `{"error": "Reading not found", "id": <id>}` with status 404 on miss.
- Returns JSON error with status 500 on storage failure.

### HTML fallback route: `POST /water-meter/readings/<record_id>/delete`

- Deletes the record with the given id.
- Redirects to `/water-meter/history` with 302 on success.
- On failure, renders an error page with 404 or 500.
- The `<record_id>` path parameter accepts strings (DynamoDB stable UUID ids are strings).

## 5. Storage responsibilities

### Facade (`app/water_meter/storage.py`)

- Add `delete_reading(record_id, db_path)` dispatching by `STORAGE_BACKEND`.
- `record_id` is the stable id (SQLite int, DynamoDB UUID string).

### SQLite (`app/water_meter/storage_sqlite.py`)

- `DELETE FROM water_meter_readings WHERE id = ?`
- Return True if a row was deleted, False otherwise.
- Existing schema unchanged.

### DynamoDB (`app/water_meter/storage_dynamodb.py`)

- Query all items for `app_id`, filter `entity_type="water_meter"`.
- Find item where stored `id` matches the given `record_id`.
- Delete using `app_id` + `created_at` key.
- Return True if deleted, False if not found.
- Only delete items where `entity_type="water_meter"` — never touch Broken Clock items.
- Existing schema and key structure unchanged.

## 6. UI behavior

- Each row in the Water Meter history table gets a delete button.
- The delete is submitted as `POST /water-meter/readings/<id>/delete`.
- Consistent Bulma styling with a small danger-colored button.
- No JavaScript required.
- The button includes a confirmation dialog via `onclick="return confirm(...)"`.

## 7. Backward compatibility rules

- Existing `GET /water-meter/history` behavior unchanged.
- Existing JSON history response shape unchanged.
- Existing `POST /water-meter/readings` form submission unchanged.
- Existing meter-name suggestions unchanged.
- SQLite remains default.
- All 98 existing tests pass without modification.

## 8. Test strategy

- All 98 existing tests pass unchanged.
- New storage tests:
  - SQLite: delete existing reading returns True and record disappears.
  - SQLite: delete missing reading returns False.
  - DynamoDB (mocked): delete existing Water Meter item returns True.
  - DynamoDB: delete missing id returns False.
  - DynamoDB: only deletes entity_type="water_meter" items, not broken_clock items.
- New route tests:
  - `DELETE /water-meter/readings/<id>` valid id returns 200 JSON.
  - `DELETE /water-meter/readings/<id>` unknown id returns 404 JSON.
  - `POST /water-meter/readings/<id>/delete` valid id redirects to history.
  - `POST /water-meter/readings/<id>/delete` unknown id returns 404 HTML.
- DynamoDB tests use mocked boto3 — no real AWS calls.
- All route tests use `tmp_path` + `monkeypatch` for DB isolation.

## 9. Security notes

- This step does not introduce auth or CSRF tokens. The app has no user concept or authentication. CSRF should be revisited when auth or user-specific record ownership is introduced.

## 10. Follow-up steps

- Add edit functionality for readings.
- Add auth when user-id scoping is needed.
- Add CSRF to all destructive POST forms.
