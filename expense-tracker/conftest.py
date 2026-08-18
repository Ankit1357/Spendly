"""Shared pytest fixtures.

Lives at the project root (next to app.py) so its directory is prepended to
sys.path, letting tests import `app` and `database.db`.
"""
import importlib

import pytest

import database.db as db


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A Flask app wired to an isolated temp database.

    get_db() reads the module global database.db.DB_PATH at call time, and
    app.py runs init_db()/seed_db() at import time. So we patch DB_PATH to a
    temp file *before* importing app, then reload app so its import-time
    init/seed runs against the temp DB. monkeypatch reverts DB_PATH after each
    test, so the real expense_tracker.db is never touched.
    """
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()

    import app as app_module
    importlib.reload(app_module)

    flask_app = app_module.app
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret")
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
