from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Module
from app.schemas import ModuleIn, ModuleOut
from app.security import DB, CurrentUser

router = APIRouter(prefix="/modules", tags=["modules"])


def own_module(db, user, module_id: int) -> Module:
    module = db.get(Module, module_id)
    # 404 rather than 403 for other people's modules, so IDs can't be probed.
    if module is None or module.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    return module


@router.get("", response_model=list[ModuleOut])
def list_modules(user: CurrentUser, db: DB):
    return db.scalars(select(Module).where(Module.owner_id == user.id).order_by(Module.code)).all()


@router.post("", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(body: ModuleIn, user: CurrentUser, db: DB):
    module = Module(owner_id=user.id, code=body.code.upper(), name=body.name)
    db.add(module)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"You already have a module {module.code}") from None
    return module


@router.put("/{module_id}", response_model=ModuleOut)
def update_module(module_id: int, body: ModuleIn, user: CurrentUser, db: DB):
    module = own_module(db, user, module_id)
    module.code, module.name = body.code.upper(), body.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"You already have a module {module.code}") from None
    return module


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(module_id: int, user: CurrentUser, db: DB):
    """Deleting a module keeps its deadlines; they just lose their module."""
    module = own_module(db, user, module_id)
    for d in module.deadlines:
        d.module_id = None
    db.delete(module)
    db.commit()
