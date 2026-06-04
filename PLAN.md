# Plan: Replace DynamoDB ordinal history IDs with stable record IDs

## 1. Why

`delete_history_record` on DynamoDB currently uses the ordinal index (1-based position in newest-first query) as the record id. If records are inserted between viewing the list and issuing a delete, the ordinal shifts and the wrong record could be deleted.

## 2. What changes

### `save_calculation` (DynamoDB)

- Generate a stable, unique id when saving.
- Use `uuid.uuid4().hex[:12]` — a short, URL-safe random hex string.
- Store it as an `id` attribute on the DynamoDB item.
- No table key change — `app_id` + `created_at` remains the primary key.

### `get_history` (DynamoDB)

- Return the stored `id` from the item instead of computing an ordinal.

### `delete_history_record` (DynamoDB)

- Query all items for the app_id.
- Find the item whose stored `id` matches the given record_id.
- Delete using `app_id` + `created_at` key.
- Return `True` if found and deleted, `False` otherwise.

### SQLite

- No changes — SQLite already uses stable auto-increment integer ids.

### Routes

- No changes needed — the `record_id` path parameter is already a string-compatible type.

### Other

- The UUID hex id is random enough for single-user use. Auth/user scoping is a separate step.

## 3. What stays the same

- `app_id` + `created_at` as DynamoDB table key.
- All route URLs and HTTP method contracts.
- All JSON response shapes (the `id` field type becomes string instead of int for DynamoDB responses; already forward-compatible).
- SQLite behavior unchanged.
- All existing tests pass with minimal updates.

## 4. Tests

- `test_dynamodb_save_calculation_writes_item` — verify item has a non-empty `id` attribute.
- `test_dynamodb_get_history_returns_stable_id` — create two records, verify each has a unique string id.
- `test_dynamodb_delete_history_record_by_stable_id` — save a record, delete by its stored id, verify success.
- `test_dynamodb_delete_history_record_not_found` — delete with a random unknown id returns False.
- Existing SQLite and route tests unchanged.
