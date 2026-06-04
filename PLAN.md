# Plan: Step 3 — Reorganize Broken Clock into a feature package

## 1. Goal

Create `app/broken_clock/` as a feature package containing domain logic, storage facade, and SQLite implementation. This groups all Broken Clock-related Python modules together without introducing Django, Blueprints, or an app factory.

## 2. Why this step is needed

Broken Clock modules are currently flat in `app/` — `broken_clock.py`, `broken_clock_storage.py`, `broken_clock_storage_sqlite.py` — alongside `app.py` and `routes.py`. Moving them into a `broken_clock/` package makes the architecture clearer for developers familiar with Django-style feature apps, while keeping the project simple.

## 3. In scope

- Create `app/broken_clock/` package directory with `__init__.py`.
- Move `app/broken_clock.py` → `app/broken_clock/domain.py`.
- Move `app/broken_clock_storage.py` → `app/broken_clock/storage.py`.
- Move `app/broken_clock_storage_sqlite.py` → `app/broken_clock/storage_sqlite.py`.
- Update imports in `app/routes.py` and test files to point to the new paths.
- Keep templates in `app/templates/broken_clock/` (unchanged).

## 4. Out of scope

- No template movement.
- No DynamoDB implementation.
- No boto3.
- No App Runner.
- No Terraform.
- No Docker or GitHub Actions changes.
- No Blueprints or app factory.
- No route URL or JSON response shape changes.
- No SQLite schema changes.
- No auth or user_id.

## 5. Target file moves

| Current path | New path |
|---|---|
| `app/broken_clock.py` | `app/broken_clock/domain.py` |
| `app/broken_clock_storage.py` | `app/broken_clock/storage.py` |
| `app/broken_clock_storage_sqlite.py` | `app/broken_clock/storage_sqlite.py` |

## 6. Import update rules

- `app/routes.py`: imports from `app.broken_clock` → `app.broken_clock.domain`. Imports from `app.broken_clock_storage` → `app.broken_clock.storage`.
- `tests/test_routes_helpers.py`: imports `_notification_class` from `app.routes` (unchanged). Imports from `app.broken_clock` nothing (only routes imports domain module).
- Files that import `app.broken_clock.domain` or `app.broken_clock.storage` or `app.broken_clock.storage_sqlite` — update their import paths.
- The new `__init__.py` can re-export key names if useful, but direct imports to the submodules are preferred for clarity.

## 7. Backward compatibility rules

- All function names and signatures are unchanged.
- `STORAGE_BACKEND` env var behavior is unchanged.
- `APP_DB_PATH` env var behavior is unchanged.
- All 41 existing tests pass after updating import paths.

## 8. Test strategy

- All 41 existing tests pass after updating import paths where needed.
- Tests that import from `app.broken_clock_storage` need updating to `app.broken_clock.storage`.
- Tests that import from `app.broken_clock_storage_sqlite` need updating to `app.broken_clock.storage_sqlite`.
- Tests that import from `app.broken_clock` (calculation helpers) need updating to `app.broken_clock.domain`.

## 9. Follow-up steps

- Move templates into `app/broken_clock/templates/` (future step).
- Add DynamoDB implementation as `app/broken_clock/storage_dynamodb.py` (future step).
