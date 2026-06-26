"""Shared test fixtures for CondoBuddy2 Core tests."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db, engine as app_engine
from app.core.security import get_password_hash, create_access_token
from app.models import User

TestAsyncSessionLocal = async_sessionmaker(
    app_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def client():
    async def init_db():
        async with app_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())

    with TestClient(app) as c:
        yield c

    async def drop_db():
        async with app_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(drop_db())


def _create_user_in_db(
    email: str,
    password: str = "testpass123",
    full_name: str = "Test User",
    role: str = "resident",
    unit_number: str = "101",
):
    """Synchronously create a user in the test DB and return (user_id, token)."""
    user_id = uuid4()
    hashed = get_password_hash(password)

    async def _insert():
        async with TestAsyncSessionLocal() as session:
            user = User(
                id=user_id,
                email=email,
                hashed_password=hashed,
                full_name=full_name,
                role=role,
                unit_number=unit_number,
            )
            session.add(user)
            await session.commit()

    asyncio.run(_insert())
    token = create_access_token(data={"sub": str(user_id)})
    return user_id, token


@pytest.fixture(scope="module")
def resident_auth(client):
    """Create a resident user and return (user_id, auth_headers)."""
    uid, token = _create_user_in_db(
        email=f"resident-{uuid4().hex[:8]}@test.com",
        role="resident",
        unit_number="101",
    )
    return uid, {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def staff_auth(client):
    """Create a staff user and return (user_id, auth_headers)."""
    uid, token = _create_user_in_db(
        email=f"staff-{uuid4().hex[:8]}@test.com",
        role="staff",
        full_name="Staff User",
        unit_number="STAFF",
    )
    return uid, {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_auth(client):
    """Create an admin user and return (user_id, auth_headers)."""
    uid, token = _create_user_in_db(
        email=f"admin-{uuid4().hex[:8]}@test.com",
        role="admin",
        full_name="Admin User",
        unit_number="ADMIN",
    )
    return uid, {"Authorization": f"Bearer {token}"}
