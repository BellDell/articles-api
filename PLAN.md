# Plan: Water Meter readings feature — MVP

## 1. Goal

Add a Water Meter readings feature as a new independent feature package `app/water_meter/`, following the same project conventions as `app/broken_clock/`. MVP covers SQLite-only storage, a form to add readings, and a history page.

## 2. Why Water Meter is a separate feature package

The project is organized into feature packages (`app/broken_clock/`). Water Meter has its own domain model, storage tables, and UX concerns. Keeping it separate avoids coupling with Broken Clock and makes it easy to deploy or test independently.

## 3. In scope

- Create `app/water_meter/` package with `__init__.py`, `domain.py`, `storage.py`, `storage_sqlite.py`.
- Add `app/templates/water_meter/form.html` and `app/templates/water_meter/history.html`.
- Add routes registered in `app/routes.py`.
- Add Home and Water Meter navigation links to the shared navbar.
- Add tests for domain validation, SQLite storage, and routes.

## 4. Out of scope

- No DynamoDB implementation in this step.
- No MySQL.
- No Terraform or App Runner changes.
- No Docker or GitHub Actions changes.
- No auth or user_id.
- No edit or delete readings.
- No charts or billing calculations.
- No changes to Broken Clock behavior.

## 5. Data model

Each reading is stored as a row in the `water_meter_readings` SQLite table:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Primary key, autoincrement |
| `created_at` | TEXT | UTC ISO-8601 timestamp |
| `reading_date` | TEXT | Date of reading in YYYY-MM-DD format |
| `meter_name` | TEXT | Defaults to "main" |
| `reading_value` | REAL | Required, non-negative numeric |
| `unit` | TEXT | Defaults to "m3" |
| `notes` | TEXT | Optional |

## 6. Routes and API design

| Route | Method | Description |
|---|---|---|
| `/water-meter` | GET | Show the add-reading form |
| `/water-meter/readings` | POST | Submit a new reading (form-data only for MVP) |
| `/water-meter/history` | GET | Show all readings newest first |

MVP uses form-data (HTML) only for submissions. Validation errors redirect back to the form with an error message. Successful submissions redirect to `/water-meter/history`.

## 7. UI/UX design

- Form page at `/water-meter` with fields: reading date, meter name (default "main"), reading value, unit (default "m3"), notes (optional).
- Submit button: "Add reading". On success: redirect to `/water-meter/history`.
- On validation error: redirect back to `/water-meter` with an error message.
- History page at `/water-meter/history`: table with columns Date, Meter, Value, Unit, Notes, newest first.
- Empty state: "No readings yet."
- Navbar gets a "Water Meter" link, active when on water-meter pages.
- Consistent dark theme and Bulma styling.

## 8. SQLite storage design

- SQLite table `water_meter_readings` in the same database file as Broken Clock (`APP_DB_PATH`).
- `app/water_meter/storage.py` is the storage facade (SQLite only for MVP).
- `app/water_meter/storage_sqlite.py` contains the SQLite implementation.
- A new `ensure_db_initialized(db_path)` helper creates the `water_meter_readings` table.
- Functions: `save_reading(...)`, `get_readings(db_path)`.
- The table is auto-created if missing (same lazy initialization pattern as Broken Clock).

## 9. DynamoDB shared-table follow-up design

When DynamoDB support is added for Water Meter:

- **Reuse the existing App Runner DynamoDB table** — do not create a second table for Water Meter.
- Separate entity types using an `entity_type` attribute on each item:
  - `entity_type = "broken_clock"` for Broken Clock records.
  - `entity_type = "water_meter"` for Water Meter records.
- New Broken Clock records should include `entity_type = "broken_clock"` (to be added when DynamoDB Water Meter is implemented).
- Legacy Broken Clock records without `entity_type` must be treated as `broken_clock`.
- Current key schema (`app_id` partition key + `created_at` sort key) remains unchanged.
- Queries filter by `entity_type` client-side after querying by `app_id` (acceptable for small data volume in a single-user app).

## 10. Test strategy

- Tests in `tests/test_water_meter_domain.py` cover validation rules.
- Tests in `tests/test_water_meter_storage.py` cover SQLite save/get.
- Tests in `tests/test_water_meter_routes.py` cover form submission, validation errors, history page, and navigation.
- Use `tmp_path` + `monkeypatch` for DB isolation.
- All 62 existing tests pass unchanged.

## 11. Follow-up steps

- Add delete/edit readings.
- Add DynamoDB backend for Water Meter using shared table + `entity_type`.
- Add/update Broken Clock DynamoDB `entity_type` tagging for new records.
- Add usage deltas and charts.
- Add JSON API support.
