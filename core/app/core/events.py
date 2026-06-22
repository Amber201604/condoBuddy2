"""Application lifecycle events."""
from fastapi import FastAPI


def setup_events(app: FastAPI):
    @app.on_event("startup")
    async def startup():
        from app.database import engine, Base
        async with engine.begin() as conn:
            # Auto-create tables for dev/test. Production should use Alembic.
            await conn.run_sync(Base.metadata.create_all)

    @app.on_event("shutdown")
    async def shutdown():
        from app.database import engine
        await engine.dispose()
