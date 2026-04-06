"""
Tests package initialization.
"""
from __future__ import annotations

import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


class AsyncSessionAdapter:
    """Tiny async wrapper around a sync SQLAlchemy session for scenario tests."""

    def __init__(self, session):
        self._session = session

    def add(self, obj):
        return self._session.add(obj)

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def commit(self):
        self._session.commit()

    async def flush(self):
        self._session.flush()

    async def refresh(self, obj):
        self._session.refresh(obj)

    async def delete(self, obj):
        self._session.delete(obj)

    async def rollback(self):
        self._session.rollback()


@pytest_asyncio.fixture
async def db_session():
    """Provide a live SQLAlchemy session for scenario simulation tests."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield AsyncSessionAdapter(session)
    finally:
        session.close()
        engine.dispose()
