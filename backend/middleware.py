"""
Production middleware stack for Bundlescope.

Includes:
- Request ID tracking
- Security headers
- Global exception handling
- Request logging
- Upload size enforcement
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("bundlescope")

# ─── Constants ───
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_CHAT_MESSAGE_LENGTH = 4000  # characters


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attaches a unique request ID to every request/response for traceability."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response (OWASP best practices)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        # Don't override Content-Type for SSE streams
        if "text/event-stream" not in response.headers.get("content-type", ""):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "%s %s → %s (%sms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects uploads that exceed the configured max size."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "POST" and "/upload" in request.url.path:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_UPLOAD_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": f"File too large. Maximum upload size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB."
                    },
                )
        return await call_next(request)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers to prevent stack trace leakage."""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("Unhandled exception [%s]: %s", request_id, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred. Please try again or contact support.",
                "request_id": request_id,
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Resource not found."},
        )


def install_middleware(app: FastAPI) -> None:
    """Installs the full production middleware stack in correct order."""
    # Order matters: outermost middleware wraps the rest.
    # Added last = runs first (outermost).
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(UploadSizeLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
