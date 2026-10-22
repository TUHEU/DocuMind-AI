"""Logging setup. Every request gets a request id, returned in the X-Request-ID header and in error bodies.
Passwords, tokens and keys are never logged: log only ids, methods, paths and status codes."""
import logging
import time
import uuid

from fastapi import FastAPI, Request


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s", force=False)


def install_request_logging(app: FastAPI) -> None:
    log = logging.getLogger("idp.request")

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        log.info("%s %s -> %s %.0fms rid=%s", request.method, request.url.path, response.status_code, ms, rid)
        return response
