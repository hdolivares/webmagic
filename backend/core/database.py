"""
Database connection and session management.
Uses SQLAlchemy with async support for PostgreSQL.
Also provides synchronous support for Celery tasks.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import AsyncGenerator
from contextlib import contextmanager
from .config import get_settings

settings = get_settings()

# Create async engine
# Note: statement_cache_size=0 is required for Supabase pooler (pgbouncer)
# which doesn't support prepared statements
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={
        "statement_cache_size": 0,
    },
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create synchronous engine for Celery tasks
# Convert postgresql+asyncpg:// to postgresql:// (psycopg2)
sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
sync_engine = create_engine(
    sync_db_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={
        "options": "-c statement_timeout=30000",  # 30 second timeout
    },
)

# Create synchronous session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
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


async def init_db() -> None:
    """
    Initialize database - create all tables.
    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db_session() -> AsyncSession:
    """
    Get a database session for async Celery tasks (DEPRECATED - use get_db_session_sync for Celery).
    Returns a new async session that should be closed after use.
    
    Usage in async Celery tasks:
        session = get_db_session()
        try:
            # Use session
            result = await session.execute(query)
            await session.commit()
        finally:
            await session.close()
    """
    return AsyncSessionLocal()


@contextmanager
def get_db_session_sync():
    """
    Context manager for synchronous database sessions (for Celery tasks).
    
    Usage in Celery tasks:
        with get_db_session_sync() as db:
            business = db.query(Business).filter(Business.id == id).first()
            db.commit()
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
