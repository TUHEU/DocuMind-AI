import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    """Identifiers are UUID strings (CHAR(36))."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Times are stored in UTC as naive datetimes (MySQL DATETIME has no zone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
