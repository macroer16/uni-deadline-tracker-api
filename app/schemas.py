from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator


class Status(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    submitted = "submitted"


class Urgency(StrEnum):
    done = "done"
    overdue = "overdue"
    due_soon = "due_soon"  # within 48 hours
    this_week = "this_week"  # within 7 days
    later = "later"


# ---- users and auth ----


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def lower(cls, v: str) -> str:
        return v.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (the OAuth2 token type, not a password)
    expires_in: int


class CalendarLink(BaseModel):
    url: str
    note: str = "Keep this link private: anyone with it can see your deadlines. Rotating it breaks the old one."


# ---- modules ----


class ModuleIn(BaseModel):
    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)


class ModuleOut(ModuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---- deadlines ----


class DeadlineBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    module_id: int | None = None
    weight_percent: int | None = Field(default=None, ge=0, le=100)
    status: Status = Status.todo
    notes: str | None = Field(default=None, max_length=5000)


class DeadlineCreate(DeadlineBase):
    # AwareDatetime rejects "2026-11-01T12:00" with no timezone, which would be ambiguous.
    due_at: AwareDatetime


class DeadlineUpdate(BaseModel):
    """Every field is optional: only the ones sent are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    module_id: int | None = None
    due_at: AwareDatetime | None = None
    weight_percent: int | None = Field(default=None, ge=0, le=100)
    status: Status | None = None
    notes: str | None = Field(default=None, max_length=5000)


class DeadlineOut(DeadlineBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    due_at: datetime
    urgency: Urgency
    module_code: str | None = None
    created_at: datetime
    updated_at: datetime
