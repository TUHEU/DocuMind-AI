from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenError, decode_access_token
from app.database.connection import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def _unauthorized(msg: str = "Authentication required") -> ApiError:
    return ApiError(401, "UNAUTHORIZED", msg, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Read the bearer token, then load the user and role from the database on EVERY request,
    so a deactivated user or a changed role takes effect immediately."""
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(creds.credentials)
    except TokenError:
        raise _unauthorized("Invalid or expired token")
    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    request.state.user_id = user.user_id
    return user


def require_roles(*roles: str):
    """Dependency factory: allow only the listed roles, otherwise 403."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "Your role is not allowed to do this")
        return user
    return checker


require_admin = require_roles("ADMIN")
