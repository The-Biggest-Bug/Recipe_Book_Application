import os
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.gettempdir(), "recipe_book_import_test.db"))

import pytest

import database
from app import app as flask_app
from app import limiter


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_users.db")
    monkeypatch.setattr(database, "DATABASE", db_path)
    database.init_database()

    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    limiter.enabled = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            yield test_client


@pytest.fixture
def rate_limited_client(client):
    limiter.enabled = True
    limiter.reset()
    yield client
    limiter.enabled = False


@pytest.fixture
def registered_user(client):
    client.post(
        "/register",
        data={
            "username": "chef",
            "email": "chef@example.com",
            "password": "letmein1",
            "confirm_password": "letmein1",
        },
    )
    return {"username": "chef", "email": "chef@example.com", "password": "letmein1"}


@pytest.fixture
def logged_in_client(client, registered_user):
    client.post(
        "/login",
        data={
            "username_or_email": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    return client
