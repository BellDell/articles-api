"""Tests for JWT authentication foundation and user registration."""

import os

import pytest
from werkzeug.security import generate_password_hash

from app.app import app
from app.auth.jwt import issue_token, verify_token, MissingJwtSecretError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    app.config["TESTING"] = True
    os.environ["APP_DB_PATH"] = str(tmp_path / "test_auth.db")
    os.environ["AUTH_USERNAME"] = "admin"
    os.environ["AUTH_PASSWORD_HASH"] = generate_password_hash("secret123")
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-testing-1234567890"
    # Default: Secure off for local tests
    os.environ["AUTH_COOKIE_SECURE"] = "false"
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# JWT helper unit tests
# ---------------------------------------------------------------------------

class TestJwtHelpers:
    @pytest.fixture(autouse=True)
    def _setup(self):
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-testing-1234567890"

    def test_issue_token_returns_string(self):
        token = issue_token("admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid(self):
        token = issue_token("alice")
        assert verify_token(token) == "alice"

    def test_verify_token_expired(self):
        token = issue_token("bob", expires_in=0)
        assert verify_token(token) is None

    def test_verify_token_bad_signature(self):
        token = issue_token("eve", expires_in=3600)
        bad_token = token[:-5] + "XXXXX"
        assert verify_token(bad_token) is None

    def test_verify_token_garbage(self):
        assert verify_token("not.a.token") is None

    def test_verify_token_empty(self):
        assert verify_token("") is None


# ---------------------------------------------------------------------------
# MissingJwtSecretError tests (JWT helper level)
# ---------------------------------------------------------------------------

class TestMissingJwtSecretError:
    """Prove MissingJwtSecretError is raised for missing/bad JWT_SECRET_KEY."""

    # --- Unset / missing ---

    def test_issue_token_missing_unset_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(MissingJwtSecretError) as exc:
            issue_token("alice")
        assert "JWT_SECRET_KEY is required" in str(exc.value)
        assert not isinstance(exc.value, KeyError)

    def test_verify_token_missing_unset_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(MissingJwtSecretError) as exc:
            verify_token("some.token.value")
        assert "JWT_SECRET_KEY is required" in str(exc.value)
        assert not isinstance(exc.value, KeyError)

    # --- Empty string ---

    def test_issue_token_empty_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "")
        with pytest.raises(MissingJwtSecretError) as exc:
            issue_token("alice")
        assert "JWT_SECRET_KEY is required" in str(exc.value)

    def test_verify_token_empty_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "")
        with pytest.raises(MissingJwtSecretError) as exc:
            verify_token("some.token.value")
        assert "JWT_SECRET_KEY is required" in str(exc.value)

    # --- Whitespace-only ---

    def test_issue_token_whitespace_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "   ")
        with pytest.raises(MissingJwtSecretError) as exc:
            issue_token("alice")
        assert "JWT_SECRET_KEY is required" in str(exc.value)

    def test_verify_token_whitespace_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "   ")
        with pytest.raises(MissingJwtSecretError) as exc:
            verify_token("some.token.value")
        assert "JWT_SECRET_KEY is required" in str(exc.value)

    # --- KeyError explicitly not raised ---

    def test_missing_does_not_raise_keyerror(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        try:
            issue_token("alice")
        except MissingJwtSecretError:
            pass
        except KeyError:
            pytest.fail("KeyError was raised instead of MissingJwtSecretError")

    # --- Existing behavior preserved when key is set ---

    def test_issue_token_works_when_set(self):
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-testing-1234567890"
        token = issue_token("alice")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_works_when_set(self):
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-testing-1234567890"
        token = issue_token("bob")
        assert verify_token(token) == "bob"


# ---------------------------------------------------------------------------
# GET /auth/login
# ---------------------------------------------------------------------------

class TestAuthLoginGet:
    def test_returns_200(self, client):
        resp = client.get("/auth/login")
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get("/auth/login")
        assert resp.content_type == "text/html" or "html" in resp.content_type

    def test_contains_login_form(self, client):
        resp = client.get("/auth/login")
        html = resp.get_data(as_text=True)
        assert 'name="username"' in html
        assert 'name="password"' in html
        assert "Login" in html
        assert "Register here" in html
        assert "css/app.css" in html


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestAuthLoginPost:
    def test_success_returns_200(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        assert resp.status_code == 200

    def test_success_returns_message(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        assert resp.get_json() == {"message": "Login successful"}

    def test_success_sets_access_token_cookie(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        assert "access_token" in resp.headers.get("Set-Cookie", "")

    def test_success_cookie_has_httponly(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        cookie = resp.headers.get("Set-Cookie", "")
        assert "HttpOnly" in cookie

    def test_success_cookie_has_samesite_lax(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        cookie = resp.headers.get("Set-Cookie", "")
        assert "SameSite=Lax" in cookie

    def test_success_cookie_not_secure_when_secure_false(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        cookie = resp.headers.get("Set-Cookie", "")
        assert "; Secure" not in cookie

    def test_success_cookie_secure_when_env_true(self, client):
        os.environ["AUTH_COOKIE_SECURE"] = "true"
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        cookie = resp.headers.get("Set-Cookie", "")
        assert "Secure" in cookie

    def test_invalid_username_returns_401(self, client):
        resp = client.post("/auth/login", json={
            "username": "unknown", "password": "secret123",
        })
        assert resp.status_code == 401

    def test_invalid_username_returns_error(self, client):
        resp = client.post("/auth/login", json={
            "username": "unknown", "password": "secret123",
        })
        assert resp.get_json() == {"error": "Invalid credentials"}

    def test_invalid_username_does_not_set_cookie(self, client):
        resp = client.post("/auth/login", json={
            "username": "unknown", "password": "secret123",
        })
        assert "access_token" not in resp.headers.get("Set-Cookie", "")

    def test_invalid_password_returns_401(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_invalid_password_returns_error(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "wrongpass",
        })
        assert resp.get_json() == {"error": "Invalid credentials"}

    def test_invalid_password_does_not_set_cookie(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "wrongpass",
        })
        assert "access_token" not in resp.headers.get("Set-Cookie", "")

    def test_missing_username_returns_400(self, client):
        resp = client.post("/auth/login", json={
            "password": "secret123",
        })
        assert resp.status_code == 400

    def test_missing_username_returns_error(self, client):
        resp = client.post("/auth/login", json={
            "password": "secret123",
        })
        assert resp.get_json() == {"error": "Username and password are required"}

    def test_missing_password_returns_400(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin",
        })
        assert resp.status_code == 400

    def test_missing_password_returns_error(self, client):
        resp = client.post("/auth/login", json={
            "username": "admin",
        })
        assert resp.get_json() == {"error": "Username and password are required"}

    def test_missing_both_returns_400(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 400

    def test_accepts_form_data(self, client):
        resp = client.post("/auth/login", data={
            "username": "admin", "password": "secret123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.headers.get("Set-Cookie", "")


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

class TestAuthLogout:
    def test_returns_200(self, client):
        resp = client.post("/auth/logout")
        assert resp.status_code == 200

    def test_returns_message(self, client):
        resp = client.post("/auth/logout")
        assert resp.get_json() == {"message": "Logged out"}

    def test_clears_cookie(self, client):
        resp = client.post("/auth/logout")
        cookie = resp.headers.get("Set-Cookie", "")
        assert "access_token=" in cookie

    def test_clearing_cookie_has_httponly(self, client):
        resp = client.post("/auth/logout")
        cookie = resp.headers.get("Set-Cookie", "")
        assert "HttpOnly" in cookie

    def test_clearing_cookie_has_samesite_lax(self, client):
        resp = client.post("/auth/logout")
        cookie = resp.headers.get("Set-Cookie", "")
        assert "SameSite=Lax" in cookie

    def test_clearing_cookie_has_max_age_zero(self, client):
        resp = client.post("/auth/logout")
        cookie = resp.headers.get("Set-Cookie", "")
        assert "Max-Age=0" in cookie

    def test_clearing_cookie_not_secure_when_secure_false(self, client):
        resp = client.post("/auth/logout")
        cookie = resp.headers.get("Set-Cookie", "")
        assert "; Secure" not in cookie

    def test_clearing_cookie_secure_when_env_true(self, client):
        os.environ["AUTH_COOKIE_SECURE"] = "true"
        resp = client.post("/auth/logout")
        cookie = resp.headers.get("Set-Cookie", "")
        assert "Secure" in cookie


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class TestAuthMe:
    def test_anonymous_returns_200(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 200

    def test_anonymous_returns_not_authenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.get_json() == {"authenticated": False}

    def test_authenticated_returns_200(self, client):
        token = issue_token("admin")
        client.set_cookie("access_token", token)
        resp = client.get("/auth/me")
        assert resp.status_code == 200

    def test_authenticated_returns_username(self, client):
        token = issue_token("admin")
        client.set_cookie("access_token", token)
        resp = client.get("/auth/me")
        assert resp.get_json() == {"authenticated": True, "username": "admin"}

    def test_invalid_token_returns_not_authenticated(self, client):
        client.set_cookie("access_token", "not-a-valid-token")
        resp = client.get("/auth/me")
        assert resp.get_json() == {"authenticated": False}

    def test_expired_token_returns_not_authenticated(self, client):
        token = issue_token("admin", expires_in=0)
        client.set_cookie("access_token", token)
        resp = client.get("/auth/me")
        assert resp.get_json() == {"authenticated": False}

    def test_missing_cookie_returns_not_authenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.get_json() == {"authenticated": False}


# ---------------------------------------------------------------------------
# GET /auth/register
# ---------------------------------------------------------------------------

class TestAuthRegisterGet:
    def test_returns_200(self, client):
        resp = client.get("/auth/register")
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get("/auth/register")
        assert "html" in resp.content_type

    def test_contains_register_form(self, client):
        resp = client.get("/auth/register")
        html = resp.get_data(as_text=True)
        assert 'name="username"' in html
        assert 'name="password"' in html
        assert 'name="confirm_password"' in html
        assert "Register" in html
        assert "Login here" in html
        assert "css/app.css" in html


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

class TestAuthRegisterPost:
    def test_success_returns_201(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "testpass123",
            "confirm_password": "testpass123",
        })
        assert resp.status_code == 201

    def test_success_returns_message(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "testpass123",
            "confirm_password": "testpass123",
        })
        assert resp.get_json() == {"message": "User registered"}

    def test_success_does_not_set_cookie(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "testpass123",
            "confirm_password": "testpass123",
        })
        cookie = resp.headers.get("Set-Cookie", "")
        assert "access_token" not in cookie

    def test_success_does_not_store_plaintext(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "testpass123",
            "confirm_password": "testpass123",
        })
        assert resp.status_code == 201
        login_resp = client.post("/auth/login", json={
            "username": "newuser", "password": "testpass123",
        })
        assert login_resp.status_code == 200
        bad_login = client.post("/auth/login", json={
            "username": "newuser", "password": "wrongpass",
        })
        assert bad_login.status_code == 401

    def test_success_no_password_hash_in_response(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "testpass123",
            "confirm_password": "testpass123",
        })
        body = resp.get_json()
        assert "password_hash" not in body
        assert "password" not in body

    def test_duplicate_username_returns_409(self, client):
        client.post("/auth/register", json={
            "username": "dupuser",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        resp = client.post("/auth/register", json={
            "username": "dupuser",
            "password": "otherpass",
            "confirm_password": "otherpass",
        })
        assert resp.status_code == 409
        assert resp.get_json() == {"error": "Username already exists"}


# ---------------------------------------------------------------------------
# Browser-style auth flow tests (Accept header based)
# ---------------------------------------------------------------------------

class TestAuthBrowserFlow:
    """Prove browser-style requests use Accept header detection for redirects/HTML."""

    def test_browser_registration_success_redirects(self, client):
        resp = client.post("/auth/register", data={
            "username": "browser_reg",
            "password": "testpass123",
            "confirm_password": "testpass123",
        }, headers={"Accept": "text/html"})
        assert resp.status_code == 302 or resp.status_code == 303
        assert "/auth/login" in resp.headers.get("Location", "")

    def test_browser_registration_validation_error_renders_html(self, client):
        resp = client.post("/auth/register", data={
            "username": "",
            "password": "pass123",
            "confirm_password": "pass123",
        }, headers={"Accept": "text/html"})
        html = resp.get_data(as_text=True)
        assert resp.status_code == 400
        assert "required" in html or "error" in html.lower()
        assert "css/app.css" in html

    def test_browser_registration_duplicate_renders_html(self, client):
        client.post("/auth/register", json={
            "username": "browser_dup",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        resp = client.post("/auth/register", data={
            "username": "browser_dup",
            "password": "otherpass",
            "confirm_password": "otherpass",
        }, headers={"Accept": "text/html"})
        html = resp.get_data(as_text=True)
        assert resp.status_code == 409
        assert "already exists" in html

    def test_browser_login_success_redirects(self, client):
        resp = client.post("/auth/login", data={
            "username": "admin",
            "password": "secret123",
        }, headers={"Accept": "text/html"})
        assert resp.status_code == 302 or resp.status_code == 303
        assert "access_token" in resp.headers.get("Set-Cookie", "")

    def test_browser_login_invalid_renders_html(self, client):
        resp = client.post("/auth/login", data={
            "username": "admin",
            "password": "wrongpass",
        }, headers={"Accept": "text/html"})
        html = resp.get_data(as_text=True)
        assert resp.status_code == 401
        assert "Invalid" in html

    def test_browser_logout_redirects(self, client):
        resp = client.post("/auth/logout", headers={"Accept": "text/html"})
        assert resp.status_code == 302 or resp.status_code == 303
        assert "/auth/login" in resp.headers.get("Location", "")


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_ok_status(self, client):
        resp = client.get("/health")
        assert resp.get_json() == {"status": "ok"}

    def test_health_log_filter_does_not_suppress_non_health(self, client):
        """Prove the filter does not affect non-health log messages."""
        import logging
        from app.app import HealthLogFilter

        flt = HealthLogFilter()

        record = logging.LogRecord(
            name="werkzeug", level=logging.INFO,
            pathname="", lineno=0,
            msg='127.0.0.1 - - [date] "GET /broken-clock HTTP/1.1" 200 -',
            args=(), exc_info=None,
        )

        assert flt.filter(record) is True

    def test_health_log_filter_suppresses_200(self, client):
        import logging
        from app.app import HealthLogFilter

        flt = HealthLogFilter()

        # Real werkzeug format includes the leading quote before GET
        record = logging.LogRecord(
            name="werkzeug", level=logging.INFO,
            pathname="", lineno=0,
            msg='127.0.0.1 - - [date] "GET /health HTTP/1.1" 200 -',
            args=(), exc_info=None,
        )

        assert flt.filter(record) is False

    def test_health_log_filter_passes_non_200(self, client):
        import logging
        from app.app import HealthLogFilter

        flt = HealthLogFilter()

        record = logging.LogRecord(
            name="werkzeug", level=logging.INFO,
            pathname="", lineno=0,
            msg='127.0.0.1 - - [date] "GET /health HTTP/1.1" 503 -',
            args=(), exc_info=None,
        )

        assert flt.filter(record) is True

    def test_case_insensitive_duplicate(self, client):
        client.post("/auth/register", json={
            "username": "CaseUser",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        resp = client.post("/auth/register", json={
            "username": "caseuser",
            "password": "otherpass",
            "confirm_password": "otherpass",
        })
        assert resp.status_code == 409
        assert resp.get_json() == {"error": "Username already exists"}

    def test_whitespace_normalized_duplicate(self, client):
        client.post("/auth/register", json={
            "username": "user",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        resp = client.post("/auth/register", json={
            "username": "  user  ",
            "password": "otherpass",
            "confirm_password": "otherpass",
        })
        assert resp.status_code == 409

    def test_missing_username_returns_400(self, client):
        resp = client.post("/auth/register", json={
            "password": "pass123",
            "confirm_password": "pass123",
        })
        assert resp.status_code == 400
        assert resp.get_json() == {
            "error": "Username, password, and confirm password are required"
        }

    def test_missing_password_returns_400(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "confirm_password": "pass123",
        })
        assert resp.status_code == 400

    def test_missing_confirm_password_returns_400(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "pass123",
        })
        assert resp.status_code == 400

    def test_whitespace_username_returns_400(self, client):
        resp = client.post("/auth/register", json={
            "username": "   ",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        assert resp.status_code == 400

    def test_whitespace_password_returns_400(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "   ",
            "confirm_password": "   ",
        })
        assert resp.status_code == 400

    def test_password_mismatch_returns_400(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "pass123",
            "confirm_password": "different",
        })
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "Passwords do not match"}

    def test_accepts_form_data(self, client):
        resp = client.post("/auth/register", data={
            "username": "formuser",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        assert resp.status_code == 201

    def test_empty_body_returns_400(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# MissingJwtSecretError route-level tests
# ---------------------------------------------------------------------------

class TestMissingJwtSecretRoute:
    """Prove MissingJwtSecretError propagates through routes when secret is missing."""

    def test_login_propagates_missing_secret(self, client, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(MissingJwtSecretError) as exc:
            client.post("/auth/login", json={
                "username": "admin", "password": "secret123",
            })
        assert "JWT_SECRET_KEY is required" in str(exc.value)
        assert not isinstance(exc.value, KeyError)

    def test_me_propagates_missing_secret(self, client, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        client.set_cookie("access_token", "some.dummy.token")
        with pytest.raises(MissingJwtSecretError) as exc:
            client.get("/auth/me")
        assert "JWT_SECRET_KEY is required" in str(exc.value)
        assert not isinstance(exc.value, KeyError)

    def test_registration_works_without_secret(self, client, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        resp = client.post("/auth/register", json={
            "username": "register_no_secret",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        assert resp.status_code == 201
        assert resp.get_json() == {"message": "User registered"}


# ---------------------------------------------------------------------------
# Login with stored users
# ---------------------------------------------------------------------------

class TestAuthLoginWithStoredUser:
    def test_registered_user_can_login(self, client):
        client.post("/auth/register", json={
            "username": "alice",
            "password": "supersecure",
            "confirm_password": "supersecure",
        })
        resp = client.post("/auth/login", json={
            "username": "alice", "password": "supersecure",
        })
        assert resp.status_code == 200
        assert resp.get_json() == {"message": "Login successful"}
        assert "access_token" in resp.headers.get("Set-Cookie", "")

    def test_wrong_password_for_stored_user_returns_401(self, client):
        client.post("/auth/register", json={
            "username": "bob",
            "password": "correctpass",
            "confirm_password": "correctpass",
        })
        resp = client.post("/auth/login", json={
            "username": "bob", "password": "wrongpass",
        })
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "Invalid credentials"}

    def test_auth_me_after_registration_login(self, client):
        client.post("/auth/register", json={
            "username": "charlie",
            "password": "pass456",
            "confirm_password": "pass456",
        })
        login_resp = client.post("/auth/login", json={
            "username": "charlie", "password": "pass456",
        })
        token = login_resp.headers.get("Set-Cookie", "")
        cookie_parts = token.split(";")
        if cookie_parts:
            raw = cookie_parts[0].split("=", 1)
            if len(raw) == 2:
                client.set_cookie("access_token", raw[1])
        me_resp = client.get("/auth/me")
        assert me_resp.get_json() == {"authenticated": True, "username": "charlie"}

    def test_stored_user_wins_over_env_fallback(self, client):
        """Stored user with same name as env-user wins."""
        client.post("/auth/register", json={
            "username": "admin",
            "password": "stored_admin_pass",
            "confirm_password": "stored_admin_pass",
        })
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "stored_admin_pass",
        })
        assert resp.status_code == 200
        resp2 = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        assert resp2.status_code == 401

    def test_env_fallback_when_no_stored_user(self, client):
        """Env fallback works when no stored user exists."""
        resp = client.post("/auth/login", json={
            "username": "admin", "password": "secret123",
        })
        assert resp.status_code == 200

    def test_response_no_password_hash_leak(self, client):
        client.post("/auth/register", json={
            "username": "noleak",
            "password": "test1234",
            "confirm_password": "test1234",
        })
        login_resp = client.post("/auth/login", json={
            "username": "noleak", "password": "test1234",
        })
        assert "password_hash" not in login_resp.get_data(as_text=True)
        me_resp = client.get("/auth/me")
        assert "password_hash" not in me_resp.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Registration error isolation tests
# ---------------------------------------------------------------------------

class TestAuthRegisterErrorIsolation:
    """Prove unexpected storage errors are NOT mapped to duplicate-user 409."""

    def test_unexpected_error_not_duplicate_409(self, client, monkeypatch):
        import app.auth.storage as auth_storage

        def broken_create(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(auth_storage, "create_user", broken_create)
        with pytest.raises(RuntimeError, match="boom"):
            client.post("/auth/register", json={
                "username": "newuser",
                "password": "pass123",
                "confirm_password": "pass123",
            })

    def test_duplicate_still_returns_409(self, client):
        client.post("/auth/register", json={
            "username": "dupuser",
            "password": "pass123",
            "confirm_password": "pass123",
        })
        resp = client.post("/auth/register", json={
            "username": "dupuser",
            "password": "otherpass",
            "confirm_password": "otherpass",
        })
        assert resp.status_code == 409
        assert resp.get_json() == {"error": "Username already exists"}
