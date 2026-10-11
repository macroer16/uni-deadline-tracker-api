from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db import Base, engine
from app.routers import auth, calendar, deadlines, modules
from app.security import DB


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for a project this size; a bigger one would use Alembic migrations instead.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Uni Deadline Tracker API",
    version="1.0.0",
    description="Track coursework deadlines by module, see what's urgent, and subscribe to them in your calendar.",
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(modules.router)
app.include_router(deadlines.router)
app.include_router(calendar.router)


@app.get("/health/live", tags=["health"])
def live():
    """The app process is up. Used as Lambda's readiness check, so a database blip can't stop it starting."""
    return {"status": "ok"}


@app.get("/health", tags=["health"])
def health(db: DB):
    """Used by Docker and the load balancer. Checks the database too, not just that the app is up."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
