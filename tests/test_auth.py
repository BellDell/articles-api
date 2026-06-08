"""Tests for JWT authentication foundation."""

import os

import pytest
from werkzeug.security import generate_password_hash

from app.app import app
from app.auth.jwt import issue_token, verify_token


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
        # Mutate token to break signature
        bad_token = token[:-5] + "XXXXX"
        assert verify_token(bad_token) is None

    def test_verify_token_garbage(self):
        assert verify_token("not.a.token") is None

    def test_verify_token_empty(self):
        assert verify_token("") is None


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
        assert 'id="login-form"' in html
        assert 'name="username"' in html
        assert 'name="password"' in html
        assert "submit" in html


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
        # When Secure is False, the cookie should NOT contain "; Secure"
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
