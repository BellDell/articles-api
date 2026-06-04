# Plan: Delete Broken Clock history records

## 1. Goal

Add the ability to delete individual Broken Clock history records from both SQLite and DynamoDB backends. Records can be removed via a JSON API (`DELETE /broken-clock/history/<id>`) or via an HTML form POST on the history page.

## 2. Why this step is needed

Users currently have no way to clean up old or unwanted calculations. Adding delete enables basic record management before introducing auth or more advanced features.

## 3. In scope

- Add `delete_history_record(record_id)` to the storage facade.
- Add SQLite implementation (delete by id, return True/False).
- Add DynamoDB implementation (scan by app_id, find matching id, delete by key).
- Add `DELETE /broken-clock/history/<record_id>` JSON route.
- Add `POST /broken-clock/history/<record_id>/delete` HTML redirect route.
- Add a delete button per row on the history HTML page.
- Add all needed tests (storage + routes).
- Keep existing JSON and HTML history response shapes unchanged.

## 4. Out of scope

- No auth, no CSRF token in this step.
- No bulk delete or delete-all.
- No undo or soft-delete.
- No Terraform changes.
- No App Runner, Docker, or GitHub Actions changes.
- No DynamoDB table schema changes.
- No data migration.

## 5. API / HTML route design

### JSON route: `DELETE /broken-clock/history/<record_id>`

- Deletes the record with the given id.
- Returns `{"deleted": true, "id": <id>}` with status 200 on success.
- Returns `{"error": "Record not found", "id": <id>}` with status 404 if no record matches.

### HTML fallback route: `POST /broken-clock/history/<record_id>/delete`

- Deletes the record with the given id.
- Redirects to `/broken-clock/history` with a 302 on success.
- On failure, renders the existing error template with status 404 or 500.
- This allows browsers (and no-JS clients) to delete records via a form POST.

### History page update

- Each row in the history table gets a delete button/form.
- The button submits a POST to `/broken-clock/history/<id>/delete`.
- The button text can be "Delete" or similar.

## 6. Storage backend responsibilities

### Facade (`app/broken_clock/storage.py`)

- Add `delete_history_record(record_id)` that dispatches to the active backend.
- `record_id` is the public-facing integer id visible in the JSON and HTML responses.

### SQLite (`app/broken_clock/storage_sqlite.py`)

- Delete the row where `id` matches the given record_id.
- Return True if a row was affected, False otherwise.

### DynamoDB (`app/broken_clock/storage_dynamodb.py`)

- Query all items for `app_id`.
- Iterate to find the item whose ordinal `id` matches the given record_id.
- Delete the item using its `app_id` + `created_at` (the DynamoDB key).
- Return True if an item was deleted, False otherwise.
- This approach avoids requiring a DynamoDB table schema change.

## 7. Backward compatibility rules

- Existing `GET /broken-clock/history` JSON and HTML behavior must not change.
- Existing record shapes must not change.
- SQLite remains the default backend.
- `STORAGE_BACKEND` behavior unchanged.
- All existing tests pass without modification.

## 8. Test strategy

- All existing 52 tests pass unchanged.
- New storage tests (SQLite + DynamoDB) cover:
  - Delete an existing record returns True.
  - Delete a non-existent record returns False.
- New route tests cover:
  - `DELETE /broken-clock/history/<id>` with valid id returns 200 JSON.
  - `DELETE /broken-clock/history/<id>` with unknown id returns 404 JSON.
  - `POST /broken-clock/history/<id>/delete` redirects to history page.
  - `POST /broken-clock/history/<id>/delete` with unknown id returns 404.
- DynamoDB tests use mocked boto3 — no real AWS calls.
- Tests use `tmp_path` + `monkeypatch` for SQLite isolation.

## 9. Follow-up security notes

- Auth should be added before deploying to production so that users cannot delete records that do not belong to them.
- A CSRF token should be added to the HTML form before production deployment.
- Bulk delete or TTL-based cleanup could be added later.
