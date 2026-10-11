from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import utcnow
from app.metrics import DEADLINES_CREATED
from app.models import Deadline
from app.routers.modules import own_module
from app.schemas import DeadlineCreate, DeadlineOut, DeadlineUpdate, Status
from app.security import DB, CurrentUser
from app.urgency import urgency

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


def to_out(d: Deadline, now) -> DeadlineOut:
    # urgency and module_code aren't database columns, so they're worked out here.
    fields = {name: getattr(d, name) for name in DeadlineOut.model_fields if name not in ("urgency", "module_code")}
    return DeadlineOut(
        **fields,
        urgency=urgency(d.due_at, d.status, now),
        module_code=d.module.code if d.module else None,
    )


def own_deadline(db, user, deadline_id: int) -> Deadline:
    d = db.get(Deadline, deadline_id)
    if d is None or d.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deadline not found")
    return d


@router.get("", response_model=list[DeadlineOut])
def list_deadlines(
    user: CurrentUser,
    db: DB,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    module_id: int | None = None,
    include_submitted: bool = True,
):
    q = select(Deadline).options(selectinload(Deadline.module)).where(Deadline.owner_id == user.id)
    if status_:
        q = q.where(Deadline.status == status_)
    if module_id is not None:
        q = q.where(Deadline.module_id == module_id)
    if not include_submitted:
        q = q.where(Deadline.status != Status.submitted)
    now = utcnow()
    return [to_out(d, now) for d in db.scalars(q.order_by(Deadline.due_at, Deadline.id))]


@router.get("/upcoming", response_model=list[DeadlineOut])
def upcoming(user: CurrentUser, db: DB, days: Annotated[int, Query(ge=1, le=365)] = 14):
    """Everything not yet submitted that is overdue or due in the next `days` days, soonest first."""
    now = utcnow()
    q = (
        select(Deadline)
        .options(selectinload(Deadline.module))
        .where(Deadline.owner_id == user.id, Deadline.status != Status.submitted, Deadline.due_at <= now + timedelta(days=days))
        .order_by(Deadline.due_at)
    )
    return [to_out(d, now) for d in db.scalars(q)]


@router.post("", response_model=DeadlineOut, status_code=status.HTTP_201_CREATED)
def create_deadline(body: DeadlineCreate, user: CurrentUser, db: DB):
    if body.module_id is not None:
        own_module(db, user, body.module_id)  # can't attach to someone else's module
    d = Deadline(owner_id=user.id, **body.model_dump())
    db.add(d)
    db.commit()
    DEADLINES_CREATED.inc()
    db.refresh(d)
    return to_out(d, utcnow())


@router.get("/{deadline_id}", response_model=DeadlineOut)
def get_deadline(deadline_id: int, user: CurrentUser, db: DB):
    return to_out(own_deadline(db, user, deadline_id), utcnow())


@router.patch("/{deadline_id}", response_model=DeadlineOut)
def update_deadline(deadline_id: int, body: DeadlineUpdate, user: CurrentUser, db: DB):
    d = own_deadline(db, user, deadline_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("module_id") is not None:
        own_module(db, user, changes["module_id"])
    for field in ("title", "due_at", "status"):
        if field in changes and changes[field] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field} can't be empty")
    for field, value in changes.items():
        setattr(d, field, value)
    db.commit()
    db.refresh(d)
    return to_out(d, utcnow())


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deadline(deadline_id: int, user: CurrentUser, db: DB):
    db.delete(own_deadline(db, user, deadline_id))
    db.commit()
