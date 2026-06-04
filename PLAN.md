# Plan: DynamoDB backend for Water Meter readings

## 1. Goal

Add an optional DynamoDB storage backend for Water Meter readings alongside the existing SQLite backend. Water Meter records are stored in the existing shared App Runner DynamoDB table, separated from Broken Clock records via an `entity_type` attribute.

## 2. Why no Terraform in this step

The existing App Runner DynamoDB table already supports both entity types. No new DynamoDB table, no GSI, and no key schema changes are needed. Water Meter records coexist with Broken Clock records using the `entity_type` attribute. Terraform updates (permissions, if needed) can be a separate follow-up.

## 3. In scope

- Add `app/water_meter/storage_dynamodb.py`.
- Update `app/water_meter/storage.py` to dispatch by `STORAGE_BACKEND` (default `sqlite`, supports `dynamodb`).
- Water Meter uses the same `DYNAMODB_TABLE` env var as Broken Clock.
- Water Meter uses shared helpers from `app/core/storage/dynamodb.py`.
- Water Meter records include `entity_type = "water_meter"`.
- `save_reading()` generates a stable UUID id.
- `get_readings()` queries by `app_id` and filters items where `entity_type == "water_meter"`.
- Returned reading shape matches the SQLite backend.
- Tests mock/stub boto3 — no real AWS calls.

## 4. Out of scope

- No Terraform changes.
- No App Runner or GitHub Actions changes.
- No new DynamoDB table or key schema changes.
- No GSI.
- No migration for existing SQLite data.
- No auth or user_id.
- No edit/delete readings.
- No charts.
- No changes to Broken Clock behavior.

## 5. DynamoDB single-table design

| Attribute | Value (Water Meter) | Value (Broken Clock) |
|---|---|---|
| `app_id` (partition key) | Environment `APP_ID` (default `articles-api`) | Same |
| `created_at` (sort key) | UTC ISO-8601 | UTC ISO-8601 |
| `entity_type` | `"water_meter"` | `"broken_clock"` (new records); legacy records may be absent |
| `id` | UUID hex (stable) | UUID hex (stable) |
| Feature fields | `reading_date`, `meter_name`, `reading_value`, `unit`, `notes` | Calculation-specific fields |

Both entity types live in the same table, share the same primary key schema, and are differentiated by `entity_type`. This keeps the existing Terraform and App Runner configuration unchanged.

Records without `entity_type` are treated as `broken_clock` (legacy support).

## 6. Backend responsibilities

### `app/water_meter/storage.py` (updated)

- Reads `STORAGE_BACKEND` env var.
- Defaults to SQLite.
- Dispatches `save_reading()` and `get_readings()` to the appropriate backend.
- Unsupported backends raise `ValueError`.

### `app/water_meter/storage_dynamodb.py` (new)

- `get_db_path()` — returns `None` (no file path needed).
- `ensure_db_initialized(db_path)` — no-op (table created by Terraform).
- `save_reading(db_path, reading_value, reading_date, meter_name, unit, notes)` — writes an item with `entity_type = "water_meter"`, stable UUID id, and all reading fields.
- `get_readings(db_path)` — queries all items for `app_id` via shared helper, filters to items where `entity_type == "water_meter"`, returns newest first with same shape as SQLite.

## 7. Backward compatibility rules

- `STORAGE_BACKEND` unset, empty, or `"sqlite"` — SQLite behavior is identical.
- `STORAGE_BACKEND=dynamodb` — Water Meter uses DynamoDB.
- Unsupported backend raises `ValueError`.
- Broken Clock behavior unchanged.
- Legacy Broken Clock records without `entity_type` are not affected.

## 8. Test strategy

- All 85 existing tests pass unchanged.
- New DynamoDB storage tests (mocked boto3, no real AWS):
  - `save_reading` writes item with `entity_type="water_meter"`.
  - `get_readings` returns only water_meter items (filters out broken_clock items).
  - `get_readings` returns newest first.
  - `get_readings` returns compatible shape (same fields as SQLite).
  - Missing `DYNAMODB_TABLE` raises clear `ValueError`.
- No real AWS calls.

## 9. Follow-up steps

- Add Terraform DynamoDB table updates if IAM permissions need broadening (likely already covered by existing policy).
- Add edit/delete for Water Meter readings.
- Add usage deltas and charts.
