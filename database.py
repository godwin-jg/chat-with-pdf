"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

# Base class for all models
Base = declarative_base()

# Lazy initialization of engine and session factory
# This prevents connection attempts during module import (e.g., for Alembic)
_engine = None
_AsyncSessionLocal = None


def _get_database_url():
    """Get database URL with correct asyncpg driver."""
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            "DATABASE_URL must use postgresql:// or postgresql+asyncpg:// protocol"
        )
    return database_url


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _get_database_url(),
            echo=settings.ENVIRONMENT == "development",
            future=True,
        )
    return _engine


def get_async_session_local():
    """Get or create the async session factory."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _AsyncSessionLocal


# For backward compatibility, provide module-level accessors
# These will initialize on first access
def __getattr__(name):
    """Lazy attribute access for engine and AsyncSessionLocal."""
    if name == "engine":
        return get_engine()
    if name == "AsyncSessionLocal":
        return get_async_session_local()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

