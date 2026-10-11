import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # A fresh database for every test, so tests can't affect each other.
    # In-memory SQLite by default; CI also runs everything against real PostgreSQL
    # by setting TEST_DATABASE_URL.
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(engine, "connect")
        def _fk_on(conn, _):  # SQLite ignores foreign keys unless asked
            conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        with TestSession() as s:
            yield s

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def signup(client, email="victor@example.com", password="correct horse battery"):
    """Register and log in; returns auth headers."""
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return signup(client)
