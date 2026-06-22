"""Async database setup for CondoBuddy2 Core."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool
from app.config import get_settings

settings = get_settings()

_pool_args = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    _pool_args = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    **_pool_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
