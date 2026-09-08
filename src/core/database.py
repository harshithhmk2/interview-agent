from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config import settings

# Setup the async database engine
# pool_pre_ping=True helps detect stale connections and reconnect automatically
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL.upper() == "DEBUG",
    future=True,
    pool_pre_ping=True
)

# Async session maker configured to return AsyncSession instances
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for database sessions. Yields an AsyncSession, 
    ensuring that the session is closed when the request lifecycle ends.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
