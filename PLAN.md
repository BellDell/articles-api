# Plan: Reject future Water Meter readings

## 1. Objective

Reject Water Meter readings whose `reading_date` is in the future. Server-side validation is authoritative. A convenience `max` attribute is added to the form's date input.

## 2. Current state (verified from disk)

### Create route

- **POST** `/water-meter/readings` → endpoint `water_meter_add_reading`
- Handler: `water_meter_add_reading()` in `app/routes.py`
- Calls `validate_reading()` from `app/water_meter/domain.py`, then `wm_storage.save_reading()` if validation passes

### Validation path (`validate_reading` in `app/water_meter/domain.py`)

Checks:
- `reading_value` — required, numeric, non-negative
- `reading_date` — required, must match `^\d{4}-\d{2}-\d{2}$` (YYYY-MM-DD format)

No date-range validation (current date vs reading date) exists today.

### Form template

- `app/templates/water_meter/form.html`
- `<input type="date" name="reading_date" id="reading_date">`
- No `max` attribute today.
- Default value: `default_reading_date` = today (set in `water_meter_form()` handler).

### Invalid-input behavior

- **JSON**: Returns `{"error": "..."}` with HTTP 400.
- **HTML form**: Redirects to `/water-meter?error=...&reading_date=...&meter_name=...&unit=...&notes=...`.
- Error messages come from `validate_reading()` error dict values.

### Flow

```
water_meter_add_reading()
  → validate_reading(reading_value, reading_date, ...)
    → if errors: return error (JSON 400 or HTML redirect)
  → rate limit check
  → wm_storage.save_reading(...)  ← future date would be stored today
  → return success
```

### Existing tests (relevant subset)

- `test_valid_html_post_redirects` — posts "2026-06-01" (past)
- `test_valid_json_post_returns_201` — posts "2026-06-01" (past)
- `test_invalid_date_redirects_with_error` — posts "bad-date"
- `test_invalid_json_post_returns_400` — posts non-numeric value

## 3. Files likely to change

| File | Change |
|------|--------|
| `app/water_meter/domain.py` | Add future-date check to `validate_reading()` |
| `app/templates/water_meter/form.html` | Add `max="{{ today }}"` to the date input |
| `tests/test_water_meter_routes.py` | Add future-date rejection tests |

## 4. Proposed backend validation design

### Add validation in `validate_reading()` (`app/water_meter/domain.py`)

After the existing regex format check, add:

```python
from datetime import date as _date

if not errors.get("reading_date"):
    try:
        parsed = _date.fromisoformat(reading_date.strip())
        if parsed > _date.today():
            errors["reading_date"] = "Reading date cannot be in the future."
    except ValueError:
        # Should not happen since regex already validated format,
        # but guard against edge cases.
        pass
```

### Import

`from datetime import date` already exists in `app/routes.py`. The `app/water_meter/domain.py` needs a new import: `from datetime import date`.

### Where validation lives

The existing `validate_reading()` already validates `reading_date` format. Adding a date-range check here is consistent with current project patterns (validation in domain layer, not in routes or storage). No changes to storage or routes.

### What stays the same

- No changes to `app/routes.py` (route handler).
- No changes to storage layer.
- No changes to response format (JSON 400 / HTML redirect with error message preserved).
- Error message key is `"reading_date"`, same as the format error. Multiple `reading_date` errors are possible (e.g., both format and future-date). The existing handler joins errors with `"; "`:

  ```python
  msg = "; ".join(errors.values())
  ```

  This means a format-invalid + future-date submission would show the format error only (since `fromisoformat` is called only if format check passes). The order of checks is:
  1. Missing reading_date → error
  2. Invalid format (regex) → error
  3. Future date (only if format passes) → error

  If format passes but date is future, the only error is "Reading date cannot be in the future."

## 5. Proposed UX `max` attribute design

In `app/templates/water_meter/form.html`, the `water_meter_form()` handler already passes `default_reading_date` (today). Add the `max` attribute:

```html
<input id="reading_date" name="reading_date" class="bc-input" type="date"
       value="{{ request.args.get('reading_date', default_reading_date) }}"
       max="{{ default_reading_date }}" autocomplete="off">
```

No changes needed to the route handler — `default_reading_date` is already `datetime.now().strftime("%Y-%m-%d")`.

This is a browser-side convenience only. Server-side validation remains authoritative.

## 6. Proposed error response behavior

### JSON path

```json
HTTP 400
{"error": "Reading date cannot be in the future."}
```

### HTML form path

Redirect to `/water-meter?error=Reading date cannot be in the future.&reading_date=2099-12-31&...`

This matches the existing invalid-input behavior pattern (redirect with query params).

## 7. Ownership/auth

No changes. The future-date check happens before storage, after authentication. Auth/ownership flow is untouched.

## 8. Code quality

- Validation addition is ~8 lines (under 20 line limit).
- No increase to cognitive complexity of `water_meter_add_reading()` (it already delegates to `validate_reading`).
- No nested functions.
- No changes to route handler length.

## 9. Tests (in `tests/test_water_meter_routes.py`)

1. `test_future_date_json_rejected` — POST with future date (JSON) returns 400 and "Reading date cannot be in the future."
2. `test_future_date_html_rejected` — POST with future date (form) redirects with error query param.
3. `test_future_date_not_saved` — POST with future date, then check history is empty.
4. `test_today_date_accepted` — POST with today's date (JSON) returns 201.
5. `test_past_date_accepted` — POST with past date (JSON) returns 201 (already covered by existing tests, kept for clarity).
6. `test_form_date_input_has_max` — GET form page includes `max="YYYY-MM-DD"` attribute.
7. All existing Water Meter route tests still pass.

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Server clock skew causing legitimate near-future dates to be rejected | Unlikely for user-entered dates; `date.today()` uses UTC-agnostic local date on the server (consistent with how dates are stored) |
| Timezone difference between user and server | The `reading_date` is a date (YYYY-MM-DD), not a datetime. No timezone context. `date.today()` on the server is the authoritative reference |
| Browser `max` attribute bypassed via curl/API | Server-side validation in `validate_reading()` is authoritative; `max` is only a UX convenience |
| `date` import in domain.py | Standard library, no risk |

## 11. What must not change

- Route endpoint: `POST /water-meter/readings` — no changes.
- Route handler: `water_meter_add_reading()` — no changes.
- Storage functions or schemas — no changes.
- SQLite — no migration.
- DynamoDB — no changes.
- Auth/ownership behavior — no changes.
- JSON response shapes — only new error message content.
- HTML redirect behavior — preserved.
- `validate_reading()` return signature — preserved (returns `(errors, cleaned)`).
- Existing error message keys — preserved.
- Broken Clock — no changes.
- Meter analytics/filtering — no changes.
- Test fixtures — preserved.

## 12. Open questions

- **Should today's date be accepted?** Yes. `reading_date == date.today()` is valid.
- **What about timezone differences?** The `reading_date` is a simple date string (YYYY-MM-DD). `date.today()` returns the server's local date. For a Flask app, this is the system timezone. This is consistent and predictable.

## 13. Validation commands

```bash
python -m pytest -q
python -W error::ResourceWarning -m pytest -q
```

## 14. Rollback notes

1. Revert `max` attribute from `app/templates/water_meter/form.html`.
2. Revert future-date check from `app/water_meter/domain.py`.
3. Revert test additions in `tests/test_water_meter_routes.py`.
4. No database, backend, or configuration changes to revert.
