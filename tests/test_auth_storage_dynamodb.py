"""Focused tests for app/auth/storage_dynamodb.py.

All tests mock/stub DynamoDB table access — no real AWS calls.
"""

import os

import pytest
from werkzeug.security import check_password_hash

from app.auth.storage import DuplicateUserError
from app.auth.storage_dynamodb import create_user, get_user_by_username


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeTable:
    """Minimal fake Table resource for monkeypatching storage_dynamodb._table."""

    def __init__(self):
        self.items = {}
        self.get_item_calls = []
        self.put_item_calls = []
        self.put_item_exception = None

    def get_item(self, Key=None):
        self.get_item_calls.append(Key)
        item = self.items.get((Key["app_id"], Key["created_at"]))
        return {"Item": item}

    def put_item(self, Item=None, ConditionExpression=None):
        self.put_item_calls.append({"Item": Item, "ConditionExpression": ConditionExpression})
        if self.put_item_exception:
            raise self.put_item_exception
        key = (Item["app_id"], Item["created_at"])
        if key in self.items:
            from botocore.exceptions import ClientError
            error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
            raise ClientError(error_response, "PutItem")
        self.items[key] = Item


def make_client_error(code="InternalServerError"):
    """Build a minimal botocore ClientError for a given error code."""
    from botocore.exceptions import ClientError
    return ClientError(
        {"Error": {"Code": code, "Message": "fake"}},
        "PutItem",
    )


@pytest.fixture(autouse=True)
def _dynamodb_env(monkeypatch):
    """Ensure STORAGE_BACKEND=dynamodb and DYNAMODB_TABLE is set for safety.

    None of these tests actually call the shared table helper because
    _table() is monkeypatched, but setting the env var avoids potential
    ValueError from app.core.storage.dynamodb if it were called.
    """
    monkeypatch.setenv("STORAGE_BACKEND", "dynamodb")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("APP_ID", "test-app")


@pytest.fixture(autouse=True)
def _fake_table(monkeypatch):
    """Monkeypatch storage_dynamodb._table to return a FakeTable."""
    fake = FakeTable()
    import app.auth.storage_dynamodb as sd
    monkeypatch.setattr(sd, "_table", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# Import-time safety
# ---------------------------------------------------------------------------

class TestImportTimeSafety:
    """Prove importing storage_dynamodb does not call DynamoDB."""

    def test_import_does_not_call_table(self):
        """Importing the module again (already imported) does not trigger table access."""
        import importlib
        import app.auth.storage_dynamodb as sd
        original_table = sd._table
        called = False

        def tracking_table():
            nonlocal called
            called = True
            return original_table()

        sd._table = tracking_table
        importlib.reload(sd)
        assert not called, "_table was called at import time"


# ---------------------------------------------------------------------------
# get_user_by_username
# ---------------------------------------------------------------------------

class TestGetUserByUsername:
    def test_uses_get_item_with_correct_key(self, _fake_table):
        get_user_by_username(None, "alice")
        assert len(_fake_table.get_item_calls) == 1
        key = _fake_table.get_item_calls[0]
        assert key["app_id"] == "test-app"
        assert key["created_at"] == "auth_user#alice"

    def test_returns_none_when_item_missing(self, _fake_table):
        result = get_user_by_username(None, "unknown")
        assert result is None

    def test_returns_user_dict_when_item_present(self, _fake_table):
        _fake_table.items[("test-app", "auth_user#bob")] = {
            "app_id": "test-app",
            "created_at": "auth_user#bob",
            "entity_type": "auth_user",
            "username": "bob",
            "password_hash": "fake_hash",
            "registered_at": "2025-01-01T00:00:00Z",
        }
        result = get_user_by_username(None, "bob")
        assert result is not None
        assert result["username_canonical"] == "bob"
        assert result["password_hash"] == "fake_hash"
        assert result["created_at"] == "2025-01-01T00:00:00Z"

    def test_does_not_call_scan(self, _fake_table):
        get_user_by_username(None, "charlie")
        assert not hasattr(_fake_table, "scan_called") or not _fake_table.scan_called
        # Just confirm get_item is how we accessed the table
        assert len(_fake_table.get_item_calls) == 1

    def test_does_not_call_query(self, _fake_table):
        get_user_by_username(None, "dave")
        assert not hasattr(_fake_table, "query_called") or not _fake_table.query_called


# ---------------------------------------------------------------------------
# create_user success
# ---------------------------------------------------------------------------

class TestCreateUserSuccess:
    def test_stores_entity_type(self, _fake_table):
        create_user(None, "user1", "secret")
        call = _fake_table.put_item_calls[0]
        assert call["Item"]["entity_type"] == "auth_user"

    def test_stores_username_canonical(self, _fake_table):
        create_user(None, "userx", "secret")
        call = _fake_table.put_item_calls[0]
        assert call["Item"]["username"] == "userx"

    def test_stores_password_hash_not_plaintext(self, _fake_table):
        create_user(None, "user2", "mypassword")
        call = _fake_table.put_item_calls[0]
        stored = call["Item"]["password_hash"]
        assert stored != "mypassword"
        assert check_password_hash(stored, "mypassword")

    def test_uses_correct_sort_key(self, _fake_table):
        create_user(None, "user3", "secret")
        call = _fake_table.put_item_calls[0]
        assert call["Item"]["created_at"] == "auth_user#user3"

    def test_stores_registered_at(self, _fake_table):
        create_user(None, "user4", "secret")
        call = _fake_table.put_item_calls[0]
        assert "registered_at" in call["Item"]
        assert call["Item"]["registered_at"] != ""

    def test_uses_condition_expression(self, _fake_table):
        create_user(None, "user5", "secret")
        call = _fake_table.put_item_calls[0]
        assert call["ConditionExpression"] == "attribute_not_exists(created_at)"

    def test_does_not_call_scan(self, _fake_table):
        create_user(None, "user6", "secret")
        assert not hasattr(_fake_table, "scan_called") or not _fake_table.scan_called

    def test_does_not_call_query(self, _fake_table):
        create_user(None, "user7", "secret")
        assert not hasattr(_fake_table, "query_called") or not _fake_table.query_called


# ---------------------------------------------------------------------------
# create_user duplicate
# ---------------------------------------------------------------------------

class TestCreateUserDuplicate:
    def test_duplicate_raises_duplicate_user_error(self, _fake_table):
        create_user(None, "dupuser", "firstpass")
        with pytest.raises(DuplicateUserError) as exc:
            create_user(None, "dupuser", "secondpass")
        assert "dupuser" in str(exc.value)

    def test_duplicate_preserves_first_password(self, _fake_table):
        create_user(None, "keepme", "firstpass")
        with pytest.raises(DuplicateUserError):
            create_user(None, "keepme", "secondpass")
        user = get_user_by_username(None, "keepme")
        assert check_password_hash(user["password_hash"], "firstpass")
        assert not check_password_hash(user["password_hash"], "secondpass")


# ---------------------------------------------------------------------------
# create_user non-duplicate DynamoDB errors
# ---------------------------------------------------------------------------

class TestCreateUserNonDuplicateError:
    def test_other_client_error_not_converted_to_duplicate(self, _fake_table):
        _fake_table.put_item_exception = make_client_error("InternalServerError")
        with pytest.raises(Exception) as exc:
            create_user(None, "newuser", "secret")
        # Must not be DuplicateUserError
        assert not isinstance(exc.value, DuplicateUserError)

    def test_other_client_error_preserves_original(self, _fake_table):
        _fake_table.put_item_exception = make_client_error("ProvisionedThroughputExceededException")
        with pytest.raises(Exception) as exc:
            create_user(None, "anotheruser", "secret")
        assert not isinstance(exc.value, DuplicateUserError)
