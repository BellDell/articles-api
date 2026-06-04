# Plan: Shared write rate limiter

## 1. Goal

Add a shared persistent rate limiter for database write/create operations. Limits writes to 5 records per 12 hours per feature (`broken_clock`, `water_meter`) per client IP. Both SQLite and DynamoDB backends are supported.

## 2. Threat model

The limiter targets accidental or intentional abuse of write endpoints by clients who know the API endpoints and call them directly. It is app-level protection, not a replacement for WAF, auth, or database access controls.

## 3. In scope

- Create `app/core/rate_limit/` package with `__init__.py`.
- Add public function `consume_write_quota(feature_name, client_ip)` returning `(allowed, retry_after_seconds)`.
- Add SQLite implementation for local/default backend.
- Add DynamoDB implementation for App Runner (atomic conditional update on shared table).
- Apply limiter to `POST /broken-clock/calculate` and `POST /water-meter/readings`.
- Return HTTP 429 with `Retry-After` header (integer seconds) when exceeded.
- Add tests for SQLite limiter, DynamoDB limiter, and route-level 429 behavior.
- DynamoDB uses hashed client IP, not raw IP.

## 4. Out of scope

- No Terraform in this step.
- No WAF, Redis, or auth.
- No CAPTCHA.
- No rate limiting for GET routes or DELETE.
- No changes to existing JSON response shapes (except the new 429 error response).
- No route URL changes.
- No changes to Broken Clock or Water Meter normal flow behavior.

## 5. Rate limit key design

### SQLite

- Table: `rate_limit_windows`
- Rows keyed by `feature_name` + `ip_hash` + `window_start`.
- A window is a fixed 12-hour bucket aligned to UTC epoch: `(now_epoch_seconds // 43200) * 43200`.
- Write increments a counter; if counter > 5 after increment, the write is blocked.

### DynamoDB

- Reuses the existing shared App Runner DynamoDB table.
- Partition key: `app_id` (same as other features).
- Sort key: a deterministic limiter key string of the form:
  `rate_limit#{feature_name}#{ip_hash}#{window_start_epoch}`
- This ensures all requests for the same feature / IP hash / 12-hour window update the same DynamoDB item atomically. The sort key is **not** a request creation timestamp — it is a deterministic bucket identifier.
- Uses a conditional update (atomic counter) to increment the write count — if count exceeds the limit, the write is rejected.
- Does not use Scan.
- Does not create table at runtime.
- Stores a hash of the client IP, not the raw IP.
- Existing table key schema unchanged: `app_id` (partition key), `created_at` (sort key, but the stored value is the deterministic bucket key described above).

### Compatibility note (DynamoDB sort key repurposing)

Rate-limit items use a non-timestamp string (`rate_limit#feature#hash#epoch`) in the `created_at` sort-key field. This does not conflict with existing consumers because:

- Existing code (`get_history`, `get_readings`, `delete_history_record`, `delete_reading`) filters by `entity_type` — rate-limit items have no `entity_type` attribute (or a distinct one) and are never returned by feature-specific queries.
- The broken-clock and water-meter DynamoDB backends query by `app_id` and then filter by `entity_type` client-side. Rate-limit items (which have no `entity_type` or a different key structure) are excluded by this filter.
- No secondary indexes, TTL policies, or external tooling currently query the DynamoDB table directly. If TTL-based cleanup is added in a follow-up, rate-limit items will need their own TTL handling.
- The App Runner instance role policy (PutItem, Query, DescribeTable) is broad enough to cover these new items without changes.

### Window type

- Uses **fixed 12-hour windows** aligned to UTC epoch (not sliding windows).
- At the boundary between two windows, up to 5 writes from the old window + 5 writes from the new window can occur in quick succession. This boundary burst is acceptable for the MVP and documented as a follow-up risk.

## 6. Backend responsibilities

### `app/core/rate_limit/__init__.py`

- Public function `consume_write_quota(feature_name, client_ip)`.
- Returns `(True, 0)` if within quota, `(False, retry_after_seconds)` if exceeded.
- `retry_after_seconds` is an integer (seconds until the current fixed window ends).
- Retrieves `app_id` from environment.
- Delegates to SQLite or DynamoDB based on `STORAGE_BACKEND`.

### `app/core/rate_limit/storage_sqlite.py`

- `consume_write_quota(feature_name, client_ip)` — uses atomic INSERT/UPDATE with counter logic.
- Creates `rate_limit_windows` table if missing (lazy init).
- Limits: 5 writes per 12-hour fixed window per feature per IP hash.

### `app/core/rate_limit/storage_dynamodb.py`

- `consume_write_quota(feature_name, client_ip)` — uses DynamoDB conditional update to atomically increment a counter.
- Limits: 5 writes per 12-hour fixed window per feature per IP hash.
- Uses hashed IP (SHA-256 truncated) as part of the deterministic sort key.
- The sort key format: `rate_limit#{feature_name}#{ip_hash}#{window_start_epoch}`.
- No table creation at runtime.
- No AWS calls at import time.

## 7. Route behavior

- `POST /broken-clock/calculate` — call limiter **after** request parsing and validation succeeds, **immediately before** the database write. Invalidation errors (400) must not consume quota.
- `POST /water-meter/readings` — same placement: after validation, before DB write.
- If the limiter allows the request but the subsequent DB write fails, the consumed quota is accepted as a tradeoff (no rollback mechanism in this step).
- 429 response shape: `{"error": "Rate limit exceeded. Try again later."}` with status 429 and `Retry-After: <seconds>` header (integer).
- Rate-limited requests must not write to the feature storage.

## 8. IP handling

- Use `request.remote_addr` for MVP (Flask's direct client IP from the request socket).
- Hash the IP with SHA-256 (first 16 hex chars) before storing in the database.
- `X-Forwarded-For` and `ProxyFix` are out of scope for this step but documented as a follow-up.

## 9. Test strategy

- All existing 107 tests pass unchanged.
- SQLite limiter tests:
  - First 5 writes are allowed.
  - 6th write in the same fixed window is blocked.
  - A new fixed window resets the quota.
  - Different IPs have independent quotas.
- DynamoDB limiter tests:
  - Uses mocked boto3 — no real AWS calls.
  - First 5 writes allowed via conditional update.
  - 6th write blocked.
  - Hashed IP is stored, not raw IP.
  - Sort key uses the deterministic `rate_limit#...` format.
- Route tests:
  - 5 normal POSTs succeed; 6th returns 429 JSON.
  - 429 response contains `Retry-After` header (integer).
  - Validating error (400) does not consume quota.
  - Existing route behavior (validation errors, success redirects) unchanged.

## 10. Follow-up steps

- Add `X-Forwarded-For` / `ProxyFix` support when behind a reverse proxy.
- Add Terraform DynamoDB TTL for automatic cleanup of expired rate limit items.
- Add rate limit for DELETE endpoints.
- Consider moving from app-level limiter to WAF-based rate limiting for production.
- Consider switching to sliding windows if fixed-window boundary bursts become an issue.
