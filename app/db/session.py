"""
Database session management for async SQLAlchemy.
Provides connection pooling and session factory.
PostgreSQL is the default (D9.1 Section 3.2), with SQLite fallback for dev.
"""

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Determine database URL: use env var if set, otherwise fallback to SQLite for dev
_env_database_url = os.environ.get("DATABASE_URL")

if _env_database_url:
    # User explicitly set DATABASE_URL - use it (PostgreSQL)
    _active_database_url = _env_database_url
    _using_sqlite_fallback = False
elif settings.USE_SQLITE_FALLBACK:
    # No DATABASE_URL set and fallback enabled - use SQLite for dev
    _active_database_url = settings.SQLITE_FALLBACK_URL
    _using_sqlite_fallback = True
    print("=" * 60)
    print("[DEV] Using SQLite fallback (DATABASE_URL not set)")
    print(f"      Database: {settings.SQLITE_FALLBACK_URL}")
    print("      Set DATABASE_URL env var for PostgreSQL")
    print("=" * 60)
else:
    # Use default PostgreSQL URL from config
    _active_database_url = settings.DATABASE_URL
    _using_sqlite_fallback = False


# Create engine based on database type
if "sqlite" in _active_database_url:
    engine = create_async_engine(
        _active_database_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )

    # SQLite does NOT enforce foreign keys by default.
    # Enable them on every connection so ON DELETE CASCADE works.
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_async_engine(
        _active_database_url,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )


def is_using_sqlite_fallback() -> bool:
    """Check if we're using the SQLite development fallback."""
    return _using_sqlite_fallback


def get_active_database_url() -> str:
    """Get the active database URL being used."""
    return _active_database_url

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Automatically handles session cleanup.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
