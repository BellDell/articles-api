"""Tests for route authorization map, login_required decorator, and access control."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.app import app
from app.core.authz import (
    PUBLIC_ENDPOINTS,
    PROTECTED_ENDPOINT_MODES,
    canonicalize_username,
    get_current_username,
    is_admin,
    authorize_ownership,
)
from tests.helpers import login


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    os.environ["APP_DB_PATH"] = str(tmp_path / "test_authz.db")
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-testing-1234567890"
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(client):
    login(client)
    return client


# ---------------------------------------------------------------------------
# Route authorization map tests
# ---------------------------------------------------------------------------

class TestRouteAuthMap:
    """Runtime route-map test: iterate app.url_map and enforce completeness."""

    def _all_endpoints(self):
        """Return set of all application endpoint names from url_map."""
        endpoints = set()
        for rule in app.url_map.iter_rules():
            ep = rule.endpoint
            # Skip Flask internal endpoints
            if ep == "static":
                continue
            endpoints.add(ep)
        return endpoints

    def test_every_endpoint_is_classified(self):
        """Every application endpoint is in PUBLIC_ENDPOINTS or PROTECTED_ENDPOINT_MODES."""
        all_eps = self._all_endpoints()
        protected_eps = set(PROTECTED_ENDPOINT_MODES.keys())
        for ep in all_eps:
            assert ep in PUBLIC_ENDPOINTS or ep in protected_eps, (
                f"Endpoint {ep!r} is not classified in PUBLIC_ENDPOINTS or PROTECTED_ENDPOINT_MODES"
            )

    def test_no_endpoint_in_both_maps(self):
        """No endpoint appears in both PUBLIC_ENDPOINTS and PROTECTED_ENDPOINT_MODES."""
        for ep in PUBLIC_ENDPOINTS:
            assert ep not in PROTECTED_ENDPOINT_MODES, (
                f"Endpoint {ep!r} is in both PUBLIC_ENDPOINTS and PROTECTED_ENDPOINT_MODES"
            )

    def test_no_broken_clock_or_water_meter_is_public(self):
        """No Broken Clock or Water Meter feature endpoint is public."""
        feature_prefixes = ("broken_clock", "water_meter", "delete_history", "delete_water_meter")
        for ep in PUBLIC_ENDPOINTS:
            for prefix in feature_prefixes:
                assert not ep.startswith(prefix), (
                    f"Feature endpoint {ep!r} should not be in PUBLIC_ENDPOINTS"
                )

    def test_all_protected_modes_valid(self):
        """Every protected endpoint has mode 'html' or 'json'."""
        for ep, mode in PROTECTED_ENDPOINT_MODES.items():
            assert mode in ("html", "json"), (
                f"Protected endpoint {ep!r} has invalid mode {mode!r}"
            )

    def test_all_mapped_endpoints_exist(self):
        """Every endpoint in the maps exists in app.url_map."""
        url_map_eps = {rule.endpoint for rule in app.url_map.iter_rules()}
        all_mapped = set(PUBLIC_ENDPOINTS) | set(PROTECTED_ENDPOINT_MODES.keys())
        for ep in all_mapped:
            assert ep in url_map_eps, (
                f"Mapped endpoint {ep!r} does not exist in app.url_map"
            )


# ---------------------------------------------------------------------------
# Anonymous access — protected HTML pages
# ---------------------------------------------------------------------------

class TestAnonymousHtmlRedirect:
    """Anonymous GET to protected browser pages redirects to /auth/login."""

    def test_anonymous_broken_clock_redirects(self, client):
        response = client.get("/broken-clock")
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"

    def test_anonymous_broken_clock_history_redirects(self, client):
        response = client.get("/broken-clock/history", headers={"Accept": "text/html"})
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"

    def test_anonymous_water_meter_redirects(self, client):
        response = client.get("/water-meter")
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"

    def test_anonymous_water_meter_history_redirects(self, client):
        response = client.get("/water-meter/history", headers={"Accept": "text/html"})
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"


# ---------------------------------------------------------------------------
# Anonymous access — protected JSON/API routes
# ---------------------------------------------------------------------------

class TestAnonymousJson401:
    """Anonymous access to protected JSON/action routes returns 401."""

    def test_anonymous_broken_clock_calculate(self, client):
        response = client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required"}

    def test_anonymous_delete_history(self, client):
        response = client.delete("/broken-clock/history/1")
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required"}

    def test_anonymous_delete_history_html(self, client):
        response = client.post("/broken-clock/history/1/delete")
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required"}

    def test_anonymous_water_meter_add_reading(self, client):
        response = client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required"}

    def test_anonymous_delete_water_meter_reading(self, client):
        response = client.delete("/water-meter/readings/1")
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required"}

    def test_anonymous_delete_water_meter_reading_html(self, client):
        response = client.post("/water-meter/readings/1/delete")
        assert response.status_code == 401
        assert response.get_json() == {"error": "Authentication required"}

    def test_anonymous_broken_clock_history_json(self, client):
        # GET /broken-clock/history with JSON Accept uses mode="html" → redirect
        response = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"

    def test_anonymous_water_meter_history_json(self, client):
        # GET /water-meter/history with JSON Accept uses mode="html" → redirect
        response = client.get("/water-meter/history", headers={"Accept": "application/json"})
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"


# ---------------------------------------------------------------------------
# Public routes remain accessible
# ---------------------------------------------------------------------------

class TestPublicRoutes:
    """Login, register, health, static, auth/me remain public."""

    def test_login_get(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200

    def test_login_post(self, client):
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "secret123",
        })
        assert response.status_code == 401  # valid because no such user yet

    def test_register_get(self, client):
        response = client.get("/auth/register")
        assert response.status_code == 200

    def test_register_post(self, client):
        response = client.post("/auth/register", json={
            "username": "newuser",
            "password": "secret123",
            "confirm_password": "secret123",
        })
        assert response.status_code == 201

    def test_logout(self, client):
        response = client.post("/auth/logout")
        assert response.status_code in (200, 302)

    def test_auth_me(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.get_json() == {"authenticated": False}

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}

    def test_static_css(self, client):
        response = client.get("/static/css/app.css")
        response.close()
        assert response.status_code in (200, 301, 308)

    def test_home(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.content_type


# ---------------------------------------------------------------------------
# Authenticated access
# ---------------------------------------------------------------------------

class TestAuthenticatedAccess:
    """Logged-in users can access protected pages."""

    def test_authed_broken_clock_form(self, authed_client):
        response = authed_client.get("/broken-clock")
        assert response.status_code == 200
        assert "text/html" in response.content_type

    def test_authed_broken_clock_calculate(self, authed_client):
        response = authed_client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        assert response.status_code == 200

    def test_authed_broken_clock_history(self, authed_client):
        response = authed_client.get("/broken-clock/history", headers={"Accept": "text/html"})
        assert response.status_code == 200

    def test_authed_water_meter_form(self, authed_client):
        response = authed_client.get("/water-meter")
        assert response.status_code == 200

    def test_authed_water_meter_add_reading(self, authed_client):
        response = authed_client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
        assert response.status_code == 201

    def test_authed_water_meter_history(self, authed_client):
        response = authed_client.get("/water-meter/history", headers={"Accept": "text/html"})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Username display
# ---------------------------------------------------------------------------

class TestUsernameDisplay:
    """Logged-in UI shows username."""

    def test_username_in_broken_clock_page(self, authed_client):
        response = authed_client.get("/broken-clock")
        text = response.get_data(as_text=True)
        assert "testuser" in text

    def test_username_in_water_meter_page(self, authed_client):
        response = authed_client.get("/water-meter")
        text = response.get_data(as_text=True)
        assert "testuser" in text

    def test_logout_button_present(self, authed_client):
        response = authed_client.get("/broken-clock")
        text = response.get_data(as_text=True)
        assert "Logout" in text
        assert "/auth/logout" in text


# ---------------------------------------------------------------------------
# Logout session tests
# ---------------------------------------------------------------------------

class TestLogout:
    """After logout, protected pages redirect to login again."""

    def test_logout_clears_session(self, authed_client):
        # Logout
        authed_client.post("/auth/logout")
        # Protected page should redirect
        response = authed_client.get("/broken-clock")
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/login"

    def test_auth_me_after_logout(self, authed_client):
        authed_client.post("/auth/logout")
        response = authed_client.get("/auth/me")
        assert response.get_json() == {"authenticated": False}


# ---------------------------------------------------------------------------
# canonicalize_username tests
# ---------------------------------------------------------------------------

class TestCanonicalizeUsername:
    def test_strips_whitespace(self):
        assert canonicalize_username("  Alice  ") == "alice"

    def test_casefolds(self):
        assert canonicalize_username("Alice") == "alice"
        assert canonicalize_username("ALICE") == "alice"

    def test_mixed_case(self):
        assert canonicalize_username("UsErNaMe") == "username"


# ---------------------------------------------------------------------------
# is_admin and authorize_ownership tests
# ---------------------------------------------------------------------------

class TestIsAdmin:
    def test_empty_env_var_returns_false(self):
        import os
        os.environ.pop("AUTH_ADMIN_USERS", None)
        assert is_admin("admin") is False

    def test_matching_admin(self, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "admin,bob")
        assert is_admin("admin") is True
        assert is_admin("bob") is True

    def test_casefolded_admin(self, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "Admin")
        assert is_admin("admin") is True

    def test_non_admin(self, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "admin")
        assert is_admin("alice") is False


class TestAuthorizeOwnership:
    def test_own_record(self):
        assert authorize_ownership("alice", "alice") is True

    def test_other_user_record(self):
        assert authorize_ownership("alice", "bob") is False

    def test_legacy_record_normal_user(self):
        assert authorize_ownership(None, "alice") is False

    def test_legacy_record_admin(self, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "admin")
        assert authorize_ownership(None, "admin") is True

    def test_admin_sees_other_user(self, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "admin")
        assert authorize_ownership("alice", "admin") is True


# ---------------------------------------------------------------------------
# Ownership isolation — Broken Clock
# ---------------------------------------------------------------------------

class TestBrokenClockOwnership:
    """User A sees only User A's records, User B sees only User B's."""

    def _register_and_login(self, client, username, password="secret123"):
        client.post("/auth/register", json={
            "username": username,
            "password": password,
            "confirm_password": password,
        })
        client.post("/auth/login", json={
            "username": username,
            "password": password,
        })

    def test_user_a_sees_own_record(self, client):
        self._register_and_login(client, "usera")
        client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        resp = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        data = resp.get_json()
        assert len(data) == 1

    def test_user_b_does_not_see_user_a_records(self, client):
        # User A creates a record
        self._register_and_login(client, "usera")
        client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        # User B logs in
        self._register_and_login(client, "userb")
        resp = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        data = resp.get_json()
        assert len(data) == 0  # User B sees no records

    def test_user_a_cannot_delete_user_b_record(self, client):
        # User A creates a record
        self._register_and_login(client, "usera")
        resp = client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        # Get the id
        history = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        rec_id = history.get_json()[0]["id"]
        # User B logs in and tries to delete
        self._register_and_login(client, "userb")
        delete_resp = client.delete(f"/broken-clock/history/{rec_id}")
        assert delete_resp.status_code == 404
        assert delete_resp.get_json()["error"] == "History record not found"


# ---------------------------------------------------------------------------
# Ownership isolation — Water Meter
# ---------------------------------------------------------------------------

class TestWaterMeterOwnership:
    """User A sees only User A's readings, User B sees only User B's."""

    def _register_and_login(self, client, username, password="secret123"):
        client.post("/auth/register", json={
            "username": username,
            "password": password,
            "confirm_password": password,
        })
        client.post("/auth/login", json={
            "username": username,
            "password": password,
        })

    def test_user_a_sees_own_reading(self, client):
        self._register_and_login(client, "usera")
        client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
        resp = client.get("/water-meter/history", headers={"Accept": "application/json"})
        data = resp.get_json()
        assert len(data) == 1

    def test_user_b_does_not_see_user_a_readings(self, client):
        self._register_and_login(client, "usera")
        client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
        self._register_and_login(client, "userb")
        resp = client.get("/water-meter/history", headers={"Accept": "application/json"})
        data = resp.get_json()
        assert len(data) == 0

    def test_user_a_cannot_delete_user_b_reading(self, client):
        self._register_and_login(client, "usera")
        client.post("/water-meter/readings", json={
            "reading_value": 100,
            "reading_date": "2026-06-01",
        })
        history = client.get("/water-meter/history", headers={"Accept": "application/json"})
        rec_id = history.get_json()[0]["id"]
        self._register_and_login(client, "userb")
        delete_resp = client.delete(f"/water-meter/readings/{rec_id}")
        assert delete_resp.status_code == 404
        assert delete_resp.get_json()["error"] == "Reading not found"


# ---------------------------------------------------------------------------
# Admin tests
# ---------------------------------------------------------------------------

class TestAdminAccess:
    """Admin users can see all records if AUTH_ADMIN_USERS is set."""

    def _register_and_login(self, client, username, password="secret123"):
        client.post("/auth/register", json={
            "username": username,
            "password": password,
            "confirm_password": password,
        })
        client.post("/auth/login", json={
            "username": username,
            "password": password,
        })

    def test_admin_sees_all_records(self, client, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "admin_user")
        # User A creates a record
        self._register_and_login(client, "user_a")
        client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        # Admin logs in
        self._register_and_login(client, "admin_user")
        resp = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        data = resp.get_json()
        assert len(data) == 1  # Admin sees all

    def test_admin_can_delete_any_record(self, client, monkeypatch):
        monkeypatch.setenv("AUTH_ADMIN_USERS", "admin_user")
        # User A creates a record
        self._register_and_login(client, "user_a")
        client.post("/broken-clock/calculate", json={
            "wrong_observed_time": "11:00",
            "real_observed_time": "10:00",
        })
        history = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        rec_id = history.get_json()[0]["id"]
        # Admin logs in and deletes
        self._register_and_login(client, "admin_user")
        delete_resp = client.delete(f"/broken-clock/history/{rec_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.get_json()["deleted"] is True


# ---------------------------------------------------------------------------
# Legacy records — hidden from normal users
# ---------------------------------------------------------------------------

class TestLegacyRecords:
    """Legacy ownerless records are hidden from normal users."""

    def test_legacy_record_hidden_from_normal_user(self, client):
        # Create a record directly in the DB without owner_username (legacy)
        from app.broken_clock.storage_sqlite import save_calculation
        db_path = os.environ["APP_DB_PATH"]
        save_calculation(db_path, "10:00", "11:00", 60, "+60", "fast",
                         ["07:00"], [{"wrong_time": "07:00", "real_time": "06:00", "day_shift": 0}])

        # Login as normal user
        client.post("/auth/register", json={
            "username": "normal_user",
            "password": "secret123",
            "confirm_password": "secret123",
        })
        client.post("/auth/login", json={
            "username": "normal_user",
            "password": "secret123",
        })
        resp = client.get("/broken-clock/history", headers={"Accept": "application/json"})
        data = resp.get_json()
        # Normal user should NOT see the legacy record
        assert len(data) == 0
