"""
Test fixtures for Bundlescope backend.

Uses an in-memory SQLite database for fast, isolated tests.
Mocks Redis cache to avoid external dependencies.
"""

import os
import sys
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis for all tests — no external dependency needed."""
    with patch("cache.pool", None), \
         patch("cache.init_cache", new_callable=AsyncMock), \
         patch("cache.close_cache", new_callable=AsyncMock), \
         patch("cache.get_cached_result", new_callable=AsyncMock, return_value=None), \
         patch("cache.set_cached_result", new_callable=AsyncMock):
        yield


@pytest_asyncio.fixture
async def test_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    from database import Base

    # Swap JSONB → JSON for SQLite compatibility
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    """Async HTTP client for testing FastAPI endpoints.

    Patches database session everywhere it's imported.
    """
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Patch everywhere async_session is imported
    patches = [
        patch("database.async_session", test_session_factory),
        patch("database.engine", test_engine),
        patch("database.init_db", new_callable=AsyncMock),
        patch("routers.upload.async_session", test_session_factory),
        patch("routers.analysis.async_session", test_session_factory),
        patch("routers.chat.async_session", test_session_factory),
        patch("services.pipeline.async_session", test_session_factory),
    ]

    for p in patches:
        p.start()

    try:
        from main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def sample_bundle_path():
    """Create a minimal valid .tar.gz for upload testing."""
    import tarfile
    import io
    import json

    tmpdir = tempfile.mkdtemp()
    bundle_path = os.path.join(tmpdir, "test-bundle.tar.gz")

    with tarfile.open(bundle_path, "w:gz") as tar:
        data = json.dumps({"gitVersion": "v1.28.0"}).encode()
        info = tarfile.TarInfo(name="cluster-resources/cluster-info/cluster_version.json")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    return bundle_path


@pytest.fixture
def sample_upload_file(sample_bundle_path):
    """Return file bytes and filename for upload testing."""
    with open(sample_bundle_path, "rb") as f:
        content = f.read()
    return content, "test-bundle.tar.gz"
