"""
Database connection module for async operations.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
)
from db.models import Base

# Cache engines by URL to avoid recreating them
_engines: dict[str, AsyncEngine] = {}


def create_engine(db_url: str) -> AsyncEngine:
    """Create or retrieve cached async database engine."""
    if db_url not in _engines:
        _engines[db_url] = create_async_engine(db_url, echo=False)
    return _engines[db_url]


def create_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session(db_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session context manager."""
    engine = create_engine(db_url)
    Session = create_session(engine)
    async with Session() as session:
        yield session


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
