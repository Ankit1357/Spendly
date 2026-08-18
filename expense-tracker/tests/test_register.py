"""Tests for the Step 2 registration flow."""
from werkzeug.security import check_password_hash

import database.db as db

VALID_PW = "supersecret"


def form(name="User", email="user@example.com", password=VALID_PW, confirm=None):
    """Build register form data; confirm_password defaults to password."""
    return {
        "name": name,
        "email": email,
        "password": password,
        "confirm_password": password if confirm is None else confirm,
    }


def test_get_renders_form(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b'name="email"' in resp.data
    assert b'name="confirm_password"' in resp.data
    assert b"Create account" in resp.data


def test_successful_registration_creates_hashed_user(client):
    resp = client.post("/register", data=form(name="Alice", email="alice@example.com"))
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")

    row = db.get_user_by_email("alice@example.com")
    assert row is not None
    assert row["name"] == "Alice"
    # Stored as a hash, not plaintext, and verifiable.
    assert row["password_hash"] != VALID_PW
    assert check_password_hash(row["password_hash"], VALID_PW)


def test_successful_registration_sets_session(client):
    client.post("/register", data=form(name="Bob", email="bob@example.com"))
    row = db.get_user_by_email("bob@example.com")
    with client.session_transaction() as sess:
        assert sess["user_id"] == row["id"]
        assert sess["user_name"] == "Bob"


def test_success_flash_shown_on_landing(client):
    resp = client.post(
        "/register",
        data=form(name="Cara", email="cara@example.com"),
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Account created successfully" in resp.data


def test_duplicate_email_rejected(client):
    client.post("/register", data=form(name="Dan", email="dan@example.com"))

    resp = client.post(
        "/register",
        data=form(name="Dan Two", email="dan@example.com", password="anotherpw"),
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data
    # No second row created; the original account is untouched.
    row = db.get_user_by_email("dan@example.com")
    assert row["name"] == "Dan"


def test_short_password_rejected(client):
    resp = client.post(
        "/register",
        data=form(name="Eve", email="eve@example.com", password="short"),
    )
    assert resp.status_code == 200
    assert b"at least 8 characters" in resp.data
    assert db.get_user_by_email("eve@example.com") is None


def test_mismatched_passwords_rejected(client):
    resp = client.post(
        "/register",
        data=form(name="Ivan", email="ivan@example.com", confirm="different-pw"),
    )
    assert resp.status_code == 200
    assert b"Passwords do not match" in resp.data
    assert db.get_user_by_email("ivan@example.com") is None


def test_blank_field_rejected_and_values_preserved(client):
    resp = client.post(
        "/register",
        data=form(name="", email="frank@example.com"),
    )
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data
    assert db.get_user_by_email("frank@example.com") is None
    # Submitted email is echoed back so the user need not retype it.
    assert b'value="frank@example.com"' in resp.data


def test_whitespace_only_name_rejected(client):
    resp = client.post(
        "/register",
        data=form(name="   ", email="grace@example.com"),
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
        data=form(name="Heidi2", email="heidi@example.com"),
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data
