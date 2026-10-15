from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.database.connection import check_database

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness check: the API process is running. Does not touch the database."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "idp-backend",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/db")
def health_db(response: Response) -> dict:
    """Readiness check: the API can reach MySQL."""
    if check_database():
        return {"status": "healthy", "database": "connected"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "unhealthy", "database": "unreachable"}
