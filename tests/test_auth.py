from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.security import create_access_token
from tests.conftest import signup


def test_register_login_and_me(client):
    headers = signup(client)
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "victor@example.com"
    assert "password" not in r.text and "hash" not in r.text


def test_email_is_case_insensitive(client):
    signup(client, email="Victor@Example.com")
    r = client.post("/auth/login", data={"username": "VICTOR@example.com", "password": "correct horse battery"})
    assert r.status_code == 200


def test_duplicate_email_rejected(client):
    signup(client)
    r = client.post("/auth/register", json={"email": "victor@example.com", "password": "another long password"})
    assert r.status_code == 409


def test_short_password_and_bad_email_rejected(client):
    assert client.post("/auth/register", json={"email": "a@example.com", "password": "short"}).status_code == 422
    assert client.post("/auth/register", json={"email": "not-an-email", "password": "long enough pw"}).status_code == 422


def test_wrong_password_and_unknown_user_get_the_same_answer(client):
    signup(client)
    wrong = client.post("/auth/login", data={"username": "victor@example.com", "password": "wrong password!"})
    unknown = client.post("/auth/login", data={"username": "nobody@example.com", "password": "wrong password!"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_password_is_hashed_with_argon2(client):
    from sqlalchemy import select

    from app.db import get_db
    from app.main import app
    from app.models import User

    signup(client)
    db = next(app.dependency_overrides[get_db]())
    stored = db.scalar(select(User)).password_hash
    assert stored.startswith("$argon2id$")
    assert "correct horse" not in stored


def test_requests_without_a_token_are_rejected(client):
    assert client.get("/me").status_code == 401
    assert client.get("/deadlines").status_code == 401


def test_expired_token_rejected(client):
    signup(client)
    old = create_access_token(1, now=datetime.now(UTC) - timedelta(hours=2))
    assert client.get("/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_token_signed_with_another_key_rejected(client):
    signup(client)
    forged = jwt.encode({"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)}, "x" * 40, algorithm="HS256")
    assert client.get("/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_unsigned_none_algorithm_token_rejected(client):
    signup(client)
    forged = jwt.encode({"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)}, None, algorithm="none")
    assert client.get("/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_token_for_deleted_user_rejected(client):
    headers = signup(client)
    assert client.delete("/me", headers=headers).status_code == 204
    assert client.get("/me", headers=headers).status_code == 401


def test_token_expiry_matches_settings(client):
    signup(client)
    r = client.post("/auth/login", data={"username": "victor@example.com", "password": "correct horse battery"})
    assert r.json()["expires_in"] == settings.token_minutes * 60


def test_settings_load_secrets_from_ssm(monkeypatch):
    """In AWS the database URL and JWT secret come from SSM Parameter Store."""
    import boto3

    from app.config import Settings

    class FakeSSM:
        def get_parameters(self, Names, WithDecryption):
            assert WithDecryption is True
            return {
                "InvalidParameters": [],
                "Parameters": [
                    {"Name": "/app/DATABASE_URL", "Value": "postgresql+psycopg://u:p@db/x"},
                    {"Name": "/app/JWT_SECRET", "Value": "s" * 40},
                ],
            }

    monkeypatch.setattr(boto3, "client", lambda name: FakeSSM())
    s = Settings(ssm_parameter_prefix="/app/", jwt_secret="")
    assert s.database_url.startswith("postgresql")
    assert s.jwt_secret == "s" * 40


def test_production_refuses_to_start_without_a_secret():
    import pytest

    from app.config import Settings

    with pytest.raises(RuntimeError):
        Settings(environment="production", jwt_secret="")
    with pytest.raises(RuntimeError):
        Settings(jwt_secret="too-short")
