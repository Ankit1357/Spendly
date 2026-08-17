import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

# db.py lives in <root>/database/db.py, so the project root is two levels up.
DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"


def get_db():
    """Return a SQLite connection with dict-like rows and foreign keys enabled.

    Foreign key enforcement is off by default in SQLite and is per-connection,
    so the PRAGMA must run on every connection. The caller owns the connection
    lifecycle and is responsible for closing it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not already exist. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert sample development data once.

    If the users table already has rows, this returns early so repeated calls
    (e.g. under the debug reloader) never duplicate data.
    """
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        expenses = [
            (user_id, 42.50, "Food", "2026-08-02", "Groceries"),
            (user_id, 18.00, "Transport", "2026-08-04", "Bus pass"),
            (user_id, 120.00, "Bills", "2026-08-05", "Electricity bill"),
            (user_id, 65.75, "Health", "2026-08-08", "Pharmacy"),
            (user_id, 30.00, "Entertainment", "2026-08-10", "Movie tickets"),
            (user_id, 89.99, "Shopping", "2026-08-12", "New shoes"),
            (user_id, 12.25, "Other", "2026-08-14", "Misc"),
            (user_id, 27.40, "Food", "2026-08-15", "Lunch out"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
