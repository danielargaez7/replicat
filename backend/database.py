import os

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://bundlescope:bundlescope_secret@localhost:5432/bundlescope",
)

# Connection pool tuning for production
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,           # Maintain 10 connections
    max_overflow=20,        # Allow up to 30 total under burst
    pool_timeout=30,        # Wait up to 30s for a connection
    pool_recycle=1800,      # Recycle connections after 30 min
    pool_pre_ping=True,     # Verify connections before use
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="pending")
    file_count = Column(Integer, default=0)
    size_bytes = Column(Integer, default=0)

    # Index for listing by time
    __table_args__ = (
        Index("idx_analyses_upload_time", "upload_time"),
        Index("idx_analyses_status", "status"),
    )


class AnalysisResultRecord(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True)
    bundle_id = Column(String, nullable=False)
    result_data = Column(JSONB, nullable=False)

    # GIN index on JSONB for querying findings by severity/namespace
    __table_args__ = (
        Index("idx_results_bundle_id", "bundle_id"),
    )


class BundleRootRecord(Base):
    __tablename__ = "bundle_roots"

    analysis_id = Column(String, primary_key=True)
    root_path = Column(String, nullable=False)


class ChatMessageRecord(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        return session
