import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from cache import close_cache, init_cache
from database import init_db
from routers import upload, analysis, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("uploads", exist_ok=True)
    await init_db()
    await init_cache()
    yield
    await close_cache()


app = FastAPI(
    title="Bundlescope",
    description="AI-Powered Kubernetes Support Bundle Analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


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
