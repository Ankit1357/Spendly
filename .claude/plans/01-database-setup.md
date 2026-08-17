# Step 1 — Database Setup

## Context

`database/db.py` in the Spendly Flask app is currently a 4-line comment stub. This step
builds the **data layer foundation** — a working SQLite implementation — that every future
feature (auth, profile, expense CRUD) depends on. The spec is
`.claude/specs/1-database-setup.md` (authoritative); this plan implements it.

**Important path note:** the actual project lives in a nested dir —
`C:\Users\ankit\Downloads\expense-tracker\expense-tracker\` (same level as `app.py`). All
paths below are relative to that root.

Outcome: on app startup the DB file is created, `users` + `expenses` tables exist with
correct constraints, a demo user (hashed password) and 8 sample expenses are seeded once,
and foreign-key enforcement works.

---

## Decisions (confirmed)

- **DB filename:** `expense_tracker.db` (underscores) at project root — mandatory to match
  the existing `.gitignore` entry so the DB stays out of git.
- **Scope:** implement the three functions in `db.py` **and** wire `init_db()` + `seed_db()`
  into `app.py` startup.
- **Passwords:** hashed with `werkzeug.security.generate_password_hash` (already installed).
- **No new pip packages.** `sqlite3` (stdlib) + `werkzeug.security` only.

---

## Files to change

1. `database/db.py` — replace stub with the full implementation.
2. `app.py` — add import + module-level startup call.

No new files, no `requirements.txt` / `.gitignore` changes.

---

## 1. `database/db.py`

Structure: imports → `DB_PATH` constant → `get_db()` → `init_db()` → `seed_db()`.

**Path (cwd-independent, via `__file__`):** `db.py` is at `<root>/database/db.py`, so root is
`Path(__file__).resolve().parent.parent`.

```python
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"
```

**`get_db()`** — connection with Row factory + FK pragma (per-connection, load-bearing).
Caller owns lifecycle; `get_db()` does not close.

```python
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

**`init_db()`** — idempotent `CREATE TABLE IF NOT EXISTS`; opens/commits/closes its own conn.

```python
def init_db():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
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
        """)
        conn.commit()
    finally:
        conn.close()
```

SQL gotchas: `DEFAULT (datetime('now'))` **requires the parentheses** (bare form is a syntax
error); `AUTOINCREMENT` needs the column spelled exactly `INTEGER PRIMARY KEY`.

**`seed_db()`** — guard on `COUNT(*) FROM users`; insert demo user then 8 expenses via
parameterized `executemany`; commit; close in `finally`.

```python
def seed_db():
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
            (user_id, 42.50,  "Food",          "2026-08-02", "Groceries"),
            (user_id, 18.00,  "Transport",     "2026-08-04", "Bus pass"),
            (user_id, 120.00, "Bills",         "2026-08-05", "Electricity bill"),
            (user_id, 65.75,  "Health",        "2026-08-08", "Pharmacy"),
            (user_id, 30.00,  "Entertainment", "2026-08-10", "Movie tickets"),
            (user_id, 89.99,  "Shopping",      "2026-08-12", "New shoes"),
            (user_id, 12.25,  "Other",         "2026-08-14", "Misc"),
            (user_id, 27.40,  "Food",          "2026-08-15", "Lunch out"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
```

All 7 fixed categories present (Food twice → 8 rows), dates spread across Aug 2026 (all
≤ today 2026-08-16), amounts as REAL, fully parameterized.

---

## 2. `app.py`

Flask 3.x removed `before_first_request`, so seed at **module level** (runs regardless of
`python app.py` vs `flask run` / WSGI). The seed guard makes the debug reloader's double-run
harmless.

- Add after the existing `from flask import ...`:
  ```python
  from database.db import get_db, init_db, seed_db
  ```
- Add immediately after `app = Flask(__name__)` (line 3), before the Routes block:
  ```python
  # Initialize and seed the database once at startup
  with app.app_context():
      init_db()
      seed_db()
  ```

The `if __name__ == "__main__":` block stays unchanged (`app.run(debug=True, port=5001)`).

---

## Pitfalls to respect (CLAUDE.md + spec)

- `PRAGMA foreign_keys = ON` on **every** connection — SQLite defaults it off; without it the
  FK clause is inert.
- `commit()` in both `init_db` and `seed_db`; `close()` in `finally`.
- Idempotency needs **both** `IF NOT EXISTS` (schema) and the `COUNT(*)` guard (seed rows).
- Parameterized SQL only — no f-strings / string concat anywhere.
- Never store the plaintext password.

---

## Verification

1. From project root, `python app.py` → starts cleanly on port 5001, no traceback.
2. `expense_tracker.db` now exists at root (`ls -la expense_tracker.db`).
3. Inspect (read-only python):
   ```python
   import sqlite3
   c = sqlite3.connect("expense_tracker.db")
   print(c.execute("SELECT COUNT(*) FROM users").fetchone()[0])       # 1
   print(c.execute("SELECT COUNT(*) FROM expenses").fetchone()[0])    # 8
   print(sorted({r[0] for r in c.execute("SELECT category FROM expenses")}))  # 7 categories
   print(c.execute("SELECT password_hash FROM users").fetchone()[0][:7])      # 'pbkdf2:'
   ```
4. **No-duplicate:** stop, re-run `python app.py`, re-query → still 1 user / 8 expenses.
5. **FK enforcement:** with `PRAGMA foreign_keys = ON`, inserting an expense with
   `user_id=99999` must raise `sqlite3.IntegrityError`.
6. Optional (spec lists no test files, so nice-to-have): `tests/test_db.py` pointing
   `db.DB_PATH` at a `tmp_path` file via monkeypatch — assert tables created, 1 user + 8
   expenses / 7 categories, second `seed_db()` no-ops, bad `user_id` raises, and
   `check_password_hash(hash, "demo123")` is True.

---

## Note on plan location

The harness restricts edits during plan mode to this plan file. You asked for the plan at
`.claude/plans/01-database-setup.md` — I'll create that copy in the project as the first step
after you approve (the `.claude/plans/` dir doesn't exist yet and will be created then).
