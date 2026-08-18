"""Tests for the Step 2 registration flow."""
from werkzeug.security import check_password_hash

import database.db as db

VALID_PW = "supersecret"


def test_get_renders_form(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b'name="email"' in resp.data
    assert b"Create account" in resp.data


def test_successful_registration_creates_hashed_user(client):
    resp = client.post(
        "/register",
        data={"name": "Alice", "email": "alice@example.com", "password": VALID_PW},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")

    row = db.get_user_by_email("alice@example.com")
    assert row is not None
    assert row["name"] == "Alice"
    # Stored as a hash, not plaintext, and verifiable.
    assert row["password_hash"] != VALID_PW
    assert check_password_hash(row["password_hash"], VALID_PW)


def test_successful_registration_sets_session(client):
    client.post(
        "/register",
        data={"name": "Bob", "email": "bob@example.com", "password": VALID_PW},
    )
    row = db.get_user_by_email("bob@example.com")
    with client.session_transaction() as sess:
        assert sess["user_id"] == row["id"]
        assert sess["user_name"] == "Bob"


def test_success_flash_shown_on_landing(client):
    resp = client.post(
        "/register",
        data={"name": "Cara", "email": "cara@example.com", "password": VALID_PW},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Account created successfully" in resp.data


def test_duplicate_email_rejected(client):
    data = {"name": "Dan", "email": "dan@example.com", "password": VALID_PW}
    client.post("/register", data=data)

    resp = client.post(
        "/register",
        data={"name": "Dan Two", "email": "dan@example.com", "password": "anotherpw"},
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data
    # No second row created; the original account is untouched.
    row = db.get_user_by_email("dan@example.com")
    assert row["name"] == "Dan"


def test_short_password_rejected(client):
    resp = client.post(
        "/register",
        data={"name": "Eve", "email": "eve@example.com", "password": "short"},
    )
    assert resp.status_code == 200
    assert b"at least 8 characters" in resp.data
    assert db.get_user_by_email("eve@example.com") is None


def test_blank_field_rejected_and_values_preserved(client):
    resp = client.post(
        "/register",
        data={"name": "", "email": "frank@example.com", "password": VALID_PW},
    )
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data
    assert db.get_user_by_email("frank@example.com") is None
    # Submitted email is echoed back so the user need not retype it.
    assert b'value="frank@example.com"' in resp.data


def test_whitespace_only_name_rejected(client):
    resp = client.post(
        "/register",
        data={"name": "   ", "email": "grace@example.com", "password": VALID_PW},
    )
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data
    assert db.get_user_by_email("grace@example.com") is None


def test_duplicate_race_returns_friendly_error(client, monkeypatch):
    """If the pre-check misses an existing email, the UNIQUE constraint still
    yields a friendly error, not a 500."""
    import app as app_module

    db.create_user("Heidi", "heidi@example.com", "x")
    # Force the pre-check to pass so the INSERT hits the UNIQUE constraint.
    monkeypatch.setattr(app_module, "get_user_by_email", lambda email: None)

    resp = client.post(
        "/register",
        data={"name": "Heidi2", "email": "heidi@example.com", "password": VALID_PW},
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data
