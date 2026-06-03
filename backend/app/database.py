"""
Database Configuration
Async SQLAlchemy setup with session management.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Force database path to be consistent regardless of where uvicorn is started
# By resolving relative to this file's folder (backend/app/database.py -> backend/marketing_ai.db)
db_url = settings.database_url
if db_url.startswith("sqlite+aiosqlite:///./"):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_name = db_url.replace("sqlite+aiosqlite:///./", "")
    db_path = os.path.join(base_dir, db_name)
    # Use forward slashes for the absolute path (SQLite handles spaces/parens fine)
    db_url = f"sqlite+aiosqlite:///{db_path.replace(os.sep, '/')}"

# Create async engine
engine = create_async_engine(
    db_url,
    echo=settings.debug,
    future=True,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
