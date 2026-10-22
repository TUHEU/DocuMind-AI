from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, users
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import install_request_logging, setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="API for document processing, OCR, validation and ERP integration.",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
install_request_logging(app)
install_error_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/", tags=["root"])
def home() -> dict:
    return {
        "message": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }
