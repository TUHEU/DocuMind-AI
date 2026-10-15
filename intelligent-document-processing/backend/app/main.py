from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API for document processing, OCR, validation and ERP integration.",
    version=settings.app_version,
)

app.include_router(health.router)


@app.get("/", tags=["root"])
def home() -> dict:
    return {
        "message": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }
