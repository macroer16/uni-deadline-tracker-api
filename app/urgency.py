"""How urgent a deadline is. Kept separate from the database so it's easy to test."""

from datetime import datetime, timedelta

from app.schemas import Status, Urgency

DUE_SOON = timedelta(hours=48)
THIS_WEEK = timedelta(days=7)


def urgency(due_at: datetime, status: str, now: datetime) -> Urgency:
    if status == Status.submitted:
        return Urgency.done
    left = due_at - now
    if left < timedelta(0):
        return Urgency.overdue
    if left <= DUE_SOON:
        return Urgency.due_soon
    if left <= THIS_WEEK:
        return Urgency.this_week
    return Urgency.later
