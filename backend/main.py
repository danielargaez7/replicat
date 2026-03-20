import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from cache import close_cache, init_cache
from database import init_db
from middleware import install_middleware
from rate_limit import limiter, rate_limit_exceeded_handler
from routers import upload, analysis, chat
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# ─── Logging ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bundlescope")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("uploads", exist_ok=True)
    await init_db()
    await init_cache()
    logger.info("Bundlescope backend started")
    yield
    await close_cache()
    logger.info("Bundlescope backend shutting down")


app = FastAPI(
    title="Bundlescope",
    description="AI-Powered Kubernetes Support Bundle Analyzer",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if os.environ.get("BUNDLESCOPE_ENV") != "production" else None,
    redoc_url=None,
)

# ─── CORS ───
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://frontend:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ─── Rate Limiting ───
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ─── Security & Observability Middleware ───
install_middleware(app)

# ─── Routers ───
app.include_router(upload.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


# ─── Health Check ───
@app.get("/health")
async def health():
    from database import async_session
    from cache import pool as redis_pool

    checks = {"api": "ok", "postgres": "ok", "redis": "ok"}
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        checks["postgres"] = "error"

    try:
        if redis_pool:
            await redis_pool.ping()
        else:
            checks["redis"] = "not_configured"
    except Exception:
        checks["redis"] = "error"

    healthy = checks["postgres"] == "ok" and checks["redis"] == "ok"
    return {"status": "ok" if healthy else "degraded", "checks": checks}
