"""Password hashing, JWT access tokens and the current-user dependency."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()  # Argon2id
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Hash of a random password, so logging in as an unknown email takes as long as a wrong
# password. Otherwise response times would reveal which emails have accounts.
_DUMMY_HASH = password_hash.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if hashed is None:
        password_hash.verify(password, _DUMMY_HASH)
        return False
    return password_hash.verify(password, hashed)


def create_access_token(user_id: int, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.token_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def hash_feed_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_feed_token() -> str:
    return secrets.token_urlsafe(32)


_unauthorised = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not signed in, or your session has expired",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]) -> User:
    try:
        # algorithms is pinned so a token can't choose "none" or a different algorithm.
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise _unauthorised from None
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorised
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]
