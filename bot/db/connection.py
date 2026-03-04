"""
Database connection module for async operations.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from db.models import Base


def create_engine(db_url: str):
    """Create async database engine."""
    return create_async_engine(db_url, echo=False)


def create_session(engine):
    """Create async session factory."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(engine) -> AsyncGenerator:
    """Dependency for getting database sessions."""
    Session = create_session(engine)
    async with Session() as session:
        yield session


async def init_db(engine):
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)