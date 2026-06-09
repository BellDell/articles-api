# Plan: Feature route protection and Water Meter ownership

## 1. Goal

Require login for feature routes and ensure Water Meter readings are visible only to their owner, with admin users allowed to see and delete all Water Meter readings.

## 2. In scope

* Add `login_required` that accepts an explicit mode, not Accept-header guessing.
* `login_required(mode="html")` redirects anonymous users to `/auth/login`.
* `login_required(mode="json")` returns HTTP 401 with `{"error": "Authentication required"}`.
* `login_required` extracts the canonical username from the existing JWT cookie.
* Canonical username rule: `username.strip().casefold()`.
* `login_required` is applied explicitly per-route, not as broad global middleware.

Protected HTML page routes (use `mode="html"`):

* `GET /broken-clock`
* `GET /broken-clock/history`
* `GET /water-meter`
* `GET /water-meter/history`

Explicit route mapping for HTML routes using `login_required(mode="html")`:

* GET /broken-clock uses login_required(mode="html")
* GET /broken-clock/history uses login_required(mode="html")
* GET /water-meter uses login_required(mode="html")
* GET /water-meter/history uses login_required(mode="html")

Protected write/delete/action routes (use `mode="json"`):

* `POST /broken-clock/calculate`
* `DELETE /broken-clock/history/<record_id>`
* `POST /broken-clock/history/<record_id>/delete`
* `POST /water-meter/readings`
* `DELETE /water-meter/readings/<record_id>`
* `POST /water-meter/readings/<record_id>/delete`

Explicit route mapping for JSON/action routes using `login_required(mode="json")`:

* POST /broken-clock/calculate uses login_required(mode="json")
* DELETE /broken-clock/history/<record_id> uses login_required(mode="json")
* POST /broken-clock/history/<record_id>/delete uses login_required(mode="json")
* POST /water-meter/readings uses login_required(mode="json")
* DELETE /water-meter/readings/<record_id> uses login_required(mode="json")
* POST /water-meter/readings/<record_id>/delete uses login_required(mode="json")

Public routes:

* `GET /`
* `GET /auth/login`
* `POST /auth/login`
* `GET /auth/register`
* `POST /auth/register`
* `POST /auth/logout`
* `GET /auth/me`
* static files

Water Meter ownership:

* New Water Meter readings store `owner_username`.
* `owner_username` is the authenticated canonical username from JWT context.
* Normal user sees only readings where `owner_username` equals current canonical username.
* Admin user sees all readings.
* Normal user can delete only their own readings.
* Admin user can delete any reading.
* Normal user deleting another user's reading returns HTTP 404 with `{"error": "Reading not found"}`.
* Normal user deleting a legacy reading without `owner_username` returns HTTP 404 with `{"error": "Reading not found"}`.
* Unauthorized access (read or delete) to another user's Water Meter record returns HTTP 404 with `{"error": "Reading not found"}`.
* Unauthorized access to a legacy ownerless Water Meter record by a normal user returns HTTP 404 with `{"error": "Reading not found"}`.
* This 404 rule applies to delete routes and any single-record read route if such a route exists.
* Admin users may read/delete any Water Meter record, including legacy ownerless records.

Admin users:

* Admins are configured with `AUTH_ADMIN_USERS`.
* `AUTH_ADMIN_USERS` is a comma-separated list of canonical usernames.
* Missing or empty `AUTH_ADMIN_USERS` means no admins.
* Parsing trims whitespace and applies `.casefold()`.

Legacy Water Meter records:

* Legacy records are records without `owner_username`.
* Legacy records without `owner_username` are hidden from normal users.
* Legacy records without `owner_username` are visible to admin users.
* Legacy records without `owner_username` are deletable by admin users.

SQLite Water Meter compatibility:

* Add an idempotent SQLite schema helper for Water Meter storage, e.g. `ensure_water_meter_schema()`.
* The helper checks whether `owner_username` column exists.
* The helper checks whether owner_username column exists.
* If `owner_username` is missing, it runs:
  `ALTER TABLE <water_meter_table> ADD COLUMN owner_username TEXT`
* If owner_username is missing, it runs ALTER TABLE on the Water Meter table to add owner_username TEXT.
* The helper is called before Water Meter insert/list/delete storage operations that depend on `owner_username`.
* The `ALTER TABLE` path is idempotent and safe for old SQLite DBs.
* The ALTER TABLE path is idempotent and safe for old SQLite DBs.
* Old SQLite DBs without `owner_username` remain readable.
* Old rows get `NULL` `owner_username` and are treated as legacy records.
* After ALTER TABLE, old rows get NULL owner_username.
* NULL owner_username is treated as a legacy ownerless record.
* Filtering by owner works for normal users.
* Admin/all-read path works.

DynamoDB Water Meter compatibility:

* DynamoDB new Water Meter items include `owner_username`.
* Normal users must only see records where `owner_username` equals current canonical username.
* Normal users must not see legacy records without `owner_username`.
* Admin users may see all records, including legacy records.
* Normal-user DynamoDB paths must not use `Scan`.
* Normal-user DynamoDB paths must not leak other users' records.
* Admin-only DynamoDB all-read path may use `Scan` as an accepted MVP tradeoff.
* Admin delete-by-id should prefer `GetItem`/conditional delete by key if current storage supports it.
* No AWS calls at import time.
* Tests mock/stub boto3 and make no real AWS calls.

Accepted DynamoDB risks:

* DynamoDB admin all-read `Scan` can be inefficient on large tables.
* This is acceptable for the current small/pet project MVP.
* No GSI/Terraform changes or DynamoDB table/index migration in this PR.

## 3. Out of scope

* Broken Clock `owner_username` storage is out of scope.
* Per-user Broken Clock history filtering is out of scope.
* Admin UI.
* Roles stored in auth user database.
* Password policy changes.
* CSS/styling changes.
* Auth form redesign.
* Route URL changes.
* Existing successful JSON response shape changes unless explicitly required for auth errors.
* Terraform changes.
* Dockerfile changes.
* GitHub Actions changes.
* Kubernetes/Argo CD changes.
* App Runner/ECR/IAM/AWS infrastructure changes.
* Database migration framework.

## 4. Behavior

* Anonymous access to protected HTML feature pages redirects to `/auth/login`.
* Anonymous `POST /water-meter/readings` returns HTTP 401 with `{"error": "Authentication required"}`.
* Anonymous protected write/delete routes return HTTP 401 with `{"error": "Authentication required"}`.
* Auth routes and static files remain public.
* Successful existing feature behavior remains unchanged for authenticated users except Water Meter data is filtered by owner.
* New Water Meter readings store `owner_username` internally.
* `owner_username` is not shown in normal user-facing HTML unless needed for admin/debug tests.
* Admin users from `AUTH_ADMIN_USERS` can view and delete all Water Meter readings.
* Normal users cannot view or delete other users' readings.
* Normal users cannot view or delete legacy readings without `owner_username`.

## 5. Backward compatibility

* Existing route URLs remain unchanged.
* Existing auth route behavior remains unchanged.
* Existing Broken Clock storage schema remains unchanged.
* Broken Clock routes require login, but Broken Clock data ownership is not changed in this PR.
* Existing Water Meter records without `owner_username` remain compatible as legacy records.
* Existing Water Meter successful form behavior remains unchanged for authenticated users.
* Existing rate limiter behavior remains unchanged.
* Existing App Runner/DynamoDB and Kubernetes/SQLite deployment config remains unchanged.
* No real AWS calls in tests.
* No AWS calls at import time.

## 6. Test strategy

`login_required` tests:

* GET /broken-clock uses login_required(mode="html").
* Anonymous `GET /broken-clock` (mode="html") redirects to `/auth/login`.
* Anonymous `GET /water-meter` (mode="html") redirects to `/auth/login`.
* POST /water-meter/readings uses login_required(mode="json").
* Anonymous `POST /water-meter/readings` (mode="json") returns HTTP 401 and `{"error": "Authentication required"}`.
* Anonymous DELETE/POST delete route (mode="json") returns HTTP 401 and `{"error": "Authentication required"}`.
* Auth routes remain public.
* `GET /` remains public.

`AUTH_ADMIN_USERS` tests:

* Missing env means no admins.
* Empty env means no admins.
* Comma-separated admins work.
* Whitespace/case variations are normalized with `.strip().casefold()`.

Water Meter ownership tests:

* New reading stores `owner_username` for authenticated user.
* User A sees only user A readings.
* User B sees only user B readings.
* Admin sees user A and user B readings.
* Normal user cannot delete another user's reading and receives HTTP 404 with `{"error": "Reading not found"}`.
* Admin can delete another user's reading.
* Legacy record without `owner_username` is hidden from normal user.
* Legacy record without `owner_username` is visible to admin.
* Admin can delete legacy record.

SQLite storage tests:

* SQLite helper adds owner_username TEXT using ALTER TABLE.
* SQLite helper is idempotent.
* `owner_username` column is added lazily if missing.
* Old DB without `owner_username` remains readable.
* Filtering by owner works.
* Admin/all-read path works.
* `ensure_water_meter_schema()` is idempotent and safe for old SQLite DBs.
* Old DB without `owner_username` gets the column added.
* Calling the helper repeatedly does not fail.
* Old rows get `NULL` `owner_username` and are treated as legacy records.
* Old rows get NULL owner_username and are treated as legacy records.

DynamoDB storage tests:

* DynamoDB new Water Meter items include `owner_username`.
* Normal-user DynamoDB tests must assert no `Scan`.
* Normal-user filtering excludes other users and legacy records.
* Legacy records without `owner_username` are visible to admin but hidden from normal users.
* Admin DynamoDB all-read tests may assert `Scan` is used or allowed.
* Admin/all-read path includes all Water Meter records including legacy records.
* Delete authorization uses owner information correctly.
* Tests mock/stub boto3 and make no real AWS calls.

Validation:

* Run `python -m pytest -q`.
* Run `python -W error::ResourceWarning -m pytest -q`.

## 7. Follow-up steps

* Add Broken Clock `owner_username` and per-user Broken Clock history filtering in a separate PR.
* Consider role storage/admin management UI in a later PR.
* Polish auth UI and extract shared CSS in a later UI-only PR.
* Replace admin-only DynamoDB `Scan` with a GSI or better key design if the dataset grows.

After writing, perform a read-only verification of PLAN.md content.

Return:

1. Confirmation that PLAN.md was overwritten, not appended.
2. Confirmation that PLAN.md contains `login_required`.
3. Confirmation that PLAN.md contains `owner_username`.
4. Confirmation that PLAN.md contains `AUTH_ADMIN_USERS`.
5. Confirmation that PLAN.md contains `anonymous POST /water-meter/readings returns HTTP 401`.
6. Confirmation that PLAN.md does not contain the forbidden phrase `Login-required route protection`.
7. Confirmation that PLAN.md does not contain the forbidden phrase `User ownership for Broken Clock or Water Meter records`.
8. Any remaining ambiguity.
