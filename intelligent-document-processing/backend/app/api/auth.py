from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import burn_password_check, create_access_token, hash_password, verify_password
from app.database.base import utcnow
from app.database.connection import get_db
from app.models import Organization, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.audit import record_audit
from app.services.email import EmailService, get_email_service, welcome_message

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

BAD_LOGIN = "Invalid e-mail or password"


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    body: RegisterRequest, request: Request, background: BackgroundTasks,
    db: Session = Depends(get_db), mailer: EmailService = Depends(get_email_service),
):
    """Public sign-up for companies and applicants. Staff roles cannot be chosen here."""
    if db.scalar(select(User.user_id).where(User.email == body.email)):
        raise ApiError(409, "CONFLICT", "An account with this e-mail already exists")
    org_id = None
    if body.role == "COMPANY":
        name = (body.organization_name or "").strip()
        if not name:
            raise ApiError(400, "VALIDATION_ERROR", "organization_name is required for a company",
                           [{"field": "organization_name", "issue": "required for role COMPANY"}])
        if db.scalar(select(Organization.org_id).where(Organization.name == name)):
            raise ApiError(409, "CONFLICT", "A company with this name already exists")
        org = Organization(name=name, registration_no=body.registration_no, country=body.country, contact_email=body.email)
        db.add(org)
        db.flush()
        org_id = org.org_id
    user = User(
        email=body.email, full_name=body.full_name.strip(), password_hash=hash_password(body.password),
        role=body.role, org_id=org_id,
    )
    db.add(user)
    try:
        db.flush()
        record_audit(db, "REGISTER", actor_id=user.user_id, entity_type="user", entity_id=user.user_id,
                     after={"role": user.role, "org_id": org_id}, request=request)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "CONFLICT", "An account with this e-mail or company already exists")
    subject, text = welcome_message(user.full_name)
    background.add_task(mailer.send, user.email, subject, text)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    s = get_settings()
    now = utcnow()
    user = db.scalar(select(User).where(User.email == body.email))

    if user is None or not user.is_active:
        burn_password_check(body.password)            # same time whether or not the e-mail exists
        raise ApiError(401, "UNAUTHORIZED", BAD_LOGIN)

    if user.locked_until and user.locked_until > now:
        wait = int((user.locked_until - now).total_seconds()) + 1
        record_audit(db, "LOGIN_BLOCKED", actor_id=user.user_id, request=request)
        db.commit()
        raise ApiError(429, "RATE_LIMITED", "Too many failed attempts. Try again later.", headers={"Retry-After": str(wait)})

    if not verify_password(body.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= s.max_failed_logins:
            user.locked_until = now + timedelta(minutes=s.lockout_minutes)
            user.failed_login_count = 0
            record_audit(db, "ACCOUNT_LOCKED", actor_id=user.user_id, request=request)
        record_audit(db, "LOGIN_FAILED", actor_id=user.user_id, request=request)
        db.commit()
        raise ApiError(401, "UNAUTHORIZED", BAD_LOGIN)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    record_audit(db, "LOGIN", actor_id=user.user_id, request=request)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.user_id, user.role),
        expires_in=s.jwt_expire_seconds,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
