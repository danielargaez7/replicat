"""
Rate limiting configuration for Bundlescope.

Uses SlowAPI (backed by limits library) to protect endpoints from abuse.
Limits are configurable via environment variables.
"""

import os
import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

logger = logging.getLogger("bundlescope")

# Default rate limits (can be overridden via env vars)
UPLOAD_RATE = os.environ.get("RATE_LIMIT_UPLOAD", "10/minute")
ANALYSIS_RATE = os.environ.get("RATE_LIMIT_ANALYSIS", "30/minute")
CHAT_RATE = os.environ.get("RATE_LIMIT_CHAT", "20/minute")
DEFAULT_RATE = os.environ.get("RATE_LIMIT_DEFAULT", "60/minute")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_RATE],
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded responses."""
    logger.warning(
        "Rate limit exceeded: %s %s from %s",
        request.method,
        request.url.path,
        get_remote_address(request),
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down and try again.",
            "retry_after": exc.detail,
        },
    )
