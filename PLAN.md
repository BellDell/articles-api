# Plan: Step 3 — Add DynamoDB history storage backend

## 1. Goal

Add a DynamoDB implementation of Broken Clock history storage alongside the existing SQLite backend. The storage facade dispatches to the correct backend based on `STORAGE_BACKEND` env var.

## 2. Why this step is needed

AWS App Runner does not provide persistent local filesystem storage, so SQLite cannot be used there. DynamoDB is the natural serverless alternative within AWS. Adding it now keeps the App Runner deployment follow-up independent of storage changes.

## 3. In scope

- Add `app/broken_clock/storage_dynamodb.py` with DynamoDB implementation.
- Add `boto3` to production dependencies.
- Update `app/broken_clock/storage.py` to dispatch to `storage_dynamodb` when `STORAGE_BACKEND=dynamodb`.
- Keep `STORAGE_BACKEND=sqlite` as default.
- Keep all four public facade function names with the same signatures.
- Preserve all SQLite behavior unchanged.
- Preserve `APP_DB_PATH` behavior for SQLite path.
- Tests use mocks/stubs for boto3 — no real AWS calls.

## 4. Out of scope

- No App Runner deployment in this step.
- No DynamoDB Terraform in this step.
- No real AWS calls in tests (mocked).
- No data migration between backends.
- No route URL or JSON response shape changes.
- No UI changes.
- No ArgoCD or Docker or GitHub Actions changes.
- No auth or user_id.

## 5. DynamoDB data model

Table: `articles-api-broken-clock-history` (configured via `DYNAMODB_TABLE` env var)

| Attribute | Type | Key | Description |
|---|---|---|---|
| `app_id` | String (S) | Partition key | Default `articles-api`, set via env var |
| `created_at` | String (S) | Sort key | UTC ISO-8601 timestamp |
| `real_observed_time` | String (S) | — | HH:MM |
| `wrong_observed_time` | String (S) | — | HH:MM |
| `offset_minutes` | Number (N) | — | Signed integer |
| `offset_human` | String (S) | — | e.g. "+60 minutes" |
| `clock_status` | String (S) | — | "fast", "slow", or "accurate" |
| `target_wrong_times` | String (S) | — | JSON array serialized |
| `reference_points` | String (S) | — | JSON array serialized |

The history response decodes `target_wrong_times` and `reference_points` from JSON strings to arrays — same shape as the SQLite backend.

Table creation belongs to Terraform, not app runtime. `ensure_db_initialized` is a no-op for DynamoDB.

## 6. Module responsibilities

### `app/broken_clock/storage_dynamodb.py` (new)

- `get_db_path()` — returns `None` (or empty string) to satisfy the facade signature.
- `ensure_db_initialized(db_path)` — no-op (table created by Terraform).
- `save_calculation(db_path, ...)` — writes an item to DynamoDB.
- `get_history(db_path)` — scans DynamoDB with the partition key, sorts descending by sort key, returns same dict shape as SQLite.

### `app/broken_clock/storage.py` (updated)

- Reads `STORAGE_BACKEND` env var.
- If `"dynamodb"`, imports from `app.broken_clock.storage_dynamodb` and delegates.
- Keeps `"sqlite"` as the default.
- `_validate_backend()` updated to accept both `"sqlite"` and `"dynamodb"`.

### `app/broken_clock/storage_sqlite.py` (unchanged)

- All existing SQLite code preserved.

## 7. Backward compatibility rules

- `STORAGE_BACKEND` unset, empty, or `"sqlite"` — SQLite behavior is byte-for-byte identical.
- `STORAGE_BACKEND=dynamodb` — all four public facade functions work with DynamoDB.
- Unsupported backend value — raises `ValueError` as before.
- `APP_DB_PATH` is only used by SQLite; DynamoDB ignores it.
- All 41 existing tests pass without modification (they use SQLite/`tmp_path`).

## 8. Test strategy

- All 41 existing SQLite tests pass unchanged.
- New tests in `tests/test_broken_clock_storage_dynamodb.py`:
  - Mock boto3 table resource.
  - Test `save_calculation` writes correct item shape.
  - Test `get_history` returns records sorted by created_at descending.
  - Test `get_history` decodes JSON string fields into arrays.
  - Test `get_db_path` returns `None`.
  - Test `ensure_db_initialized` is a no-op.
- All tests use monkeypatch for env vars and mocks for AWS. No real AWS calls.

## 9. Follow-up steps

- Add DynamoDB table Terraform under `infra/aws/dynamodb/`.
- Add App Runner deployment configuration.
- Add `boto3` to Docker image (already available in CI/pip requirements).
