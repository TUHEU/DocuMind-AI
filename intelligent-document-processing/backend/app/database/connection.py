from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create the SQLAlchemy engine lazily so the API can start without MySQL."""
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def check_database() -> bool:
    """Return True if a simple query succeeds against MySQL."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
