from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.errors import ApiError, not_found
from app.core.security import hash_password
from app.database.connection import get_db
from app.models import Organization, User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/api/v1/users", tags=["Admin"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.scalar(select(User.user_id).where(User.email == body.email)):
        raise ApiError(409, "CONFLICT", "An account with this e-mail already exists")
    if body.org_id and db.get(Organization, body.org_id) is None:
        raise ApiError(400, "VALIDATION_ERROR", "Unknown organization", [{"field": "org_id", "issue": "does not exist"}])
    user = User(email=body.email, full_name=body.full_name.strip(), password_hash=hash_password(body.password),
                role=body.role, org_id=body.org_id)
    db.add(user)
    try:
        db.flush()
        record_audit(db, "USER_CREATE", actor_id=admin.user_id, entity_type="user", entity_id=user.user_id,
                     after={"role": user.role}, request=request)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "CONFLICT", "An account with this e-mail already exists")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User")
    if user.user_id == admin.user_id and (
        (body.role is not None and body.role != "ADMIN") or body.is_active is False
    ):
        raise ApiError(409, "INVALID_STATE", "An administrator cannot remove their own admin access")
    before = {"role": user.role, "is_active": bool(user.is_active)}
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = 1 if body.is_active else 0
    record_audit(db, "USER_UPDATE", actor_id=admin.user_id, entity_type="user", entity_id=user.user_id,
                 before=before, after={"role": user.role, "is_active": bool(user.is_active)}, request=request)
    db.commit()
    return user
