# Plan: Shared storage infrastructure refactor

## 1. Goal

Extract reusable DynamoDB storage plumbing from `app/broken_clock/storage_dynamodb.py` into `app/core/storage/dynamodb.py` — a shared module that future feature packages (Water Meter) can use alongside Broken Clock. The `app/broken_clock/` package keeps its feature-specific logic, storage facade, and backend files.

## 2. Why this refactor is needed before Water Meter

`app/broken_clock/storage_dynamodb.py` contains both generic DynamoDB infrastructure (table lookup, query pagination) and Broken Clock-specific mapping (JSON encoding/decoding of calculation fields). Before a second feature package needs DynamoDB access, these generic parts should live in a shared location to avoid duplication.

## 3. In scope

- Create `app/core/storage/` package with `__init__.py`.
- Create `app/core/storage/dynamodb.py` with generic DynamoDB helpers.
- Move `_get_table()` and `_query_all_items()` helpers from `app/broken_clock/storage_dynamodb.py` into `app/core/storage/dynamodb.py`.
- The shared helpers accept a table name argument rather than reading `DYNAMODB_TABLE` from env — the caller is responsible for providing the table name.
- Update `app/broken_clock/storage_dynamodb.py` to import and use the shared helpers.
- Keep the Broken Clock `save_calculation`, `get_history`, and `delete_history_record` functions in the Broken Clock package — they contain feature-specific logic.

## 4. Out of scope

- No Water Meter implementation.
- No changes to `app/broken_clock/storage.py` (public facade).
- No changes to `app/broken_clock/storage_sqlite.py`.
- No route or JSON response shape changes.
- No Terraform or App Runner changes.
- No auth or user_id.
- No migrations.
- No renaming files to "repository" in this step.

## 5. Target responsibilities

### `app/core/storage/dynamodb.py` (new)

- `get_dynamodb_table(table_name)` — returns a DynamoDB Table resource. Reads `DYNAMODB_TABLE` from env if `table_name` is `None`.
- `query_all_items(table, hash_key_name, hash_key_value)` — runs a DynamoDB query with pagination, returns all items sorted newest first (by sort key descending).
- No Flask dependency. No Broken Clock domain logic.

### `app/broken_clock/storage_dynamodb.py` (updated)

- Imports from `app.core.storage.dynamodb`.
- Calls `get_dynamodb_table()` to get the table.
- Calls `query_all_items()` for history and delete queries.
- Keeps all feature-specific logic: JSON encoding/decoding of calculation fields, history response shape, delete by stable id.

## 6. Backward compatibility rules

- All public function signatures in `app/broken_clock/storage.py` unchanged.
- All DynamoDB behavior (table name, env vars, pagination, ordering, response shapes) unchanged.
- SQLite behavior unchanged.
- All 60 existing tests pass without modification.

## 7. Test strategy

- All 60 existing tests pass unchanged.
- No test changes needed — the shared helpers are tested indirectly through existing DynamoDB tests.
- If desired, a separate test file for the shared helpers can be added in a follow-up step.

## 8. Follow-up steps

- Implement Water Meter feature with its own storage backends (`app/water_meter/storage_sqlite.py`, `app/water_meter/storage_dynamodb.py`) using the shared infrastructure.
- Optionally add a shared SQLite helper to `app/core/storage/sqlite.py` if table creation and connection lifecycle logic can be parameterized.
