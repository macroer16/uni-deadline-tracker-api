from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.config import settings
from app.metrics import LOGIN_FAILURES, USERS_REGISTERED
from app.models import User
from app.schemas import CalendarLink, Token, UserCreate, UserOut
from app.security import (
    DB,
    CurrentUser,
    create_access_token,
    hash_feed_token,
    hash_password,
    new_feed_token,
    verify_password,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: DB):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    USERS_REGISTERED.inc()
    return user


@router.post("/auth/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    # Same message for "no such user" and "wrong password", so emails can't be discovered.
    if not verify_password(form.password, user.password_hash if user else None):
        LOGIN_FAILURES.inc()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(user.id), expires_in=settings.token_minutes * 60)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/me/calendar-link", response_model=CalendarLink)
def rotate_calendar_link(user: CurrentUser, db: DB, request: Request):
    """Create (or replace) the private calendar link. Only its hash is stored."""
    token = new_feed_token()
    user.feed_token_hash = hash_feed_token(token)
    db.commit()
    return CalendarLink(url=str(request.url_for("calendar_feed", token=token)))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: CurrentUser, db: DB):
    """Deletes the account and everything in it (modules and deadlines cascade)."""
    db.delete(user)
    db.commit()
