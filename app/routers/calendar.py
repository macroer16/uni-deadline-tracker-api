from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import utcnow
from app.ics import build_calendar
from app.models import Deadline, User
from app.security import DB, hash_feed_token

router = APIRouter(tags=["calendar"])


@router.get("/calendar/{token}.ics", name="calendar_feed")
def calendar_feed(token: str, request: Request, db: DB):
    """Calendar apps can't send a login token, so this uses a long random secret in the URL instead.
    Only its hash is stored, so a database leak doesn't expose working links."""
    user = db.scalar(select(User).where(User.feed_token_hash == hash_feed_token(token)))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar not found")
    deadlines = db.scalars(
        select(Deadline).options(selectinload(Deadline.module)).where(Deadline.owner_id == user.id).order_by(Deadline.due_at)
    ).all()
    body = build_calendar(list(deadlines), request.url.hostname or "localhost", utcnow())
    return Response(body, media_type="text/calendar; charset=utf-8", headers={"Cache-Control": "private, max-age=300"})
