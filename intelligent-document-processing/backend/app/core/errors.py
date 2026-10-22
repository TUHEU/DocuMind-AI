"""One error format for the whole API, as in the Phase 2 contract:
{"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("idp.errors")

_CODE_BY_STATUS = {
    400: "VALIDATION_ERROR", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED", 409: "CONFLICT", 413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE", 422: "VALIDATION_ERROR", 429: "RATE_LIMITED",
}


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None, headers: dict | None = None):
        self.status_code, self.code, self.message = status_code, code, message
        self.details, self.headers = details, headers


def not_found(what: str = "Resource") -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what} not found")


def _body(request: Request, code: str, message: str, details: list | None = None) -> dict:
    err = {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}
    if details:
        err["details"] = details
    return {"error": err}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(_body(request, exc.code, exc.message, exc.details), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        code = _CODE_BY_STATUS.get(exc.status_code, "ERROR")
        return JSONResponse(_body(request, code, str(exc.detail)), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "issue": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body(request, "VALIDATION_ERROR", "Request is not valid", details), status_code=400)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        # Full detail goes to the log only; the client gets a generic message (no stack trace, no paths).
        log.exception("Unhandled error request_id=%s", getattr(request.state, "request_id", None))
        return JSONResponse(_body(request, "INTERNAL_ERROR", "Unexpected server error"), status_code=500)
