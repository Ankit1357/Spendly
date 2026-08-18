# Spec: Registration

## Overview
This feature turns the existing static `/register` page into a working sign-up
flow. It adds a `POST /register` handler that validates the submitted form,
rejects duplicate emails and weak passwords, hashes the password with werkzeug,
persists the new user via a dedicated `database/db.py` helper, and logs the user
in by establishing a Flask session. It sits at Step 2 of the Spendly roadmap:
Step 1 delivered the `users`/`expenses` schema and DB helpers, and registration
is the first feature that actually writes user data and introduces the session
infrastructure that every later authenticated step (logout, profile, expenses)
will build on.

## Depends on
- **Step 1 — Database setup** (`.claude/specs/1-database-setup.md`): requires the
  `users` table (`id, name, email UNIQUE, password_hash, created_at`) and the
  `get_db()` / `init_db()` / `seed_db()` helpers. This branch is cut from
  `feature/database-setup`, which contains that work (it is **not** on `main`).

## Routes
- `POST /register` — process the sign-up form: validate input, create the user,
  start a session, redirect on success — **public**
- `GET /register` — already implemented (renders `register.html`); it will be
  extended so the same view function handles both GET and POST — **public**

No other new routes. (Login POST and logout are separate roadmap steps and are
out of scope here.)

## Database changes
No schema changes — the `users` table from Step 1 is sufficient.

New helper functions in `database/db.py` (DB logic must not live in routes):
- `create_user(name, email, password_hash)` — inserts a row into `users` and
  returns the new user id; uses a parameterized `INSERT`.
- `get_user_by_email(email)` — returns the user row (or `None`) via a
  parameterized `SELECT`, used to enforce email uniqueness before insert.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/base.html` — add a flash-message region inside the content block
    (render `get_flashed_messages(with_categories=true)`) so success/error
    notices appear consistently across pages.
  - `templates/register.html` — no structural change required; it already posts
    to `/register` with fields `name`, `email`, `password` and renders an
    `{{ error }}` block. Confirm the error variable is passed on validation
    failure and that the form re-populates `name`/`email` on error (re-render
    with submitted values so the user does not retype them).

## Files to change
- `expense-tracker/app.py` — set `app.secret_key` for sessions; extend the
  `register()` view to accept `GET` and `POST`; add validation, call the new DB
  helpers, set `session['user_id']` / `session['user_name']`, flash and redirect.
- `expense-tracker/database/db.py` — add `create_user()` and
  `get_user_by_email()`.
- `expense-tracker/templates/base.html` — flash message rendering.
- `expense-tracker/templates/register.html` — ensure error + value re-population.

## Files to create
None.

## New dependencies
No new dependencies. `flask==3.1.3` (sessions, `request.form`, `redirect`,
`url_for`, `flash`, `session`) and `werkzeug==3.1.6`
(`generate_password_hash`) are already in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash` — never store
  plaintext; never log the raw password.
- DB logic belongs in `database/db.py` — the route calls helpers, no inline SQL.
- Use `url_for()` for every internal link/redirect — never hardcode URLs.
- Use CSS variables from `style.css` — never hardcode hex values; reuse the
  existing `.auth-error` styling for validation messages.
- All templates extend `base.html`.
- Use `abort()` for HTTP errors, not bare string returns.
- Keep the app on **port 5001**; do not change existing run config.
- Validation rules: `name`, `email`, `password` all required; password minimum
  8 characters (matches the form placeholder); duplicate email must be rejected
  with a friendly error, not a raw `sqlite3.IntegrityError`.
- Secret key should come from an environment variable with a dev fallback, not a
  value that changes per request (sessions must survive across requests).

## Definition of done
- Running `python app.py` starts the server on port 5001 with no errors.
- `GET /register` still renders the sign-up form.
- Submitting the form with a new name/email/password creates exactly one row in
  the `users` table with a hashed (non-plaintext) `password_hash`, then redirects
  the user to a logged-in landing state with a success flash message.
- After successful registration the Flask `session` contains the new user's id
  (verifiable in a test client or by a subsequent authenticated request).
- Submitting an email that already exists (e.g. `demo@spendly.com`) re-renders
  `register.html` with a visible error and creates **no** new user row.
- Submitting a password shorter than 8 characters re-renders the form with an
  error and creates no user row.
- Submitting with any of `name`/`email`/`password` blank re-renders the form with
  an error and creates no user row; previously entered `name`/`email` are
  preserved in the inputs.
- No SQL is written inline in `app.py`; all queries go through `database/db.py`
  helpers using `?` placeholders.
- `pytest` passes (including any new tests covering success, duplicate email, and
  short password).
