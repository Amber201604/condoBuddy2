"""CondoBuddy2 Core — Integration tests."""
import os
import sys

# MUST set before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

os.environ["REDIS_URL"] = ""
os.environ["CELERY_BROKER_URL"] = ""
os.environ["MINIO_ENDPOINT"] = ""
os.environ["MQTT_BROKER_HOST"] = ""

sys.path.insert(0, "/root/.openclaw/workspace/condobuddy2/core")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db, engine as app_engine

TestAsyncSessionLocal = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    import asyncio
    
    # Create tables in the same engine that app uses
    async def init_db():
        async with app_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(init_db())
    
    with TestClient(app) as c:
        yield c
    
    # Drop tables
    async def drop_db():
        async with app_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    asyncio.run(drop_db())


class TestHealth:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestAuth:
    def test_register_and_login(self, client):
        # Register
        response = client.post("/api/v1/auth/register", json={
            "email": "admin@test.com",
            "password": "admin123",
            "full_name": "Admin User",
            "role": "admin"
        })
        assert response.status_code in [200, 201]

        # Login
        response = client.post("/api/v1/auth/login", data={
            "username": "admin@test.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestFacilityBookingWebhook:
    def test_facility_booking_webhook(self, client):
        """FastAPI should accept facility booking webhook from Frappe"""
        payload = {
            "booking_id": "FB-2026-00001",
            "facility": "FAC-Meeting Room A",
            "resident": "RES-0001",
            "unit": "UNIT-101",
            "booking_date": "2026-06-25",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "status": "Pending",
            "event": "created"
        }
        response = client.post("/api/v1/webhooks/facility-booking", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "received"


class TestVisitorWebhook:
    def test_visitor_webhook(self, client):
        """FastAPI should accept visitor webhook from Frappe"""
        payload = {
            "visitor_id": "VIS-2026-00001",
            "visitor_name": "Test Guest",
            "visitor_phone": "555-0100",
            "host_resident": "RES-0001",
            "host_unit": "UNIT-101",
            "visit_type": "Guest",
            "expected_arrival": "2026-06-22T14:00:00",
            "expected_departure": "2026-06-22T16:00:00",
            "qr_code": "abc123",
            "status": "Pre-registered"
        }
        response = client.post("/api/v1/webhooks/visitor", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "received"


class TestIoTAlert:
    def test_iot_alert_webhook(self, client):
        """FastAPI should accept IoT alert webhook"""
        payload = {
            "device_id": "SEN-SMOKE-001",
            "location": "Hallway 3A",
            "timestamp": "2026-06-22T12:00:00",
            "event_type": "Smoke Detected",
            "type": "iot",
            "message": "Smoke detected in hallway"
        }
        response = client.post("/api/v1/webhooks/iot-alert", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "received"


class TestAccessLog:
    def test_access_log_webhook(self, client):
        """FastAPI should accept access log webhook"""
        payload = {
            "timestamp": "2026-06-22T12:00:00",
            "event_type": "Entry",
            "device_id": "GATE-MAIN-001",
            "location": "Main Gate",
            "resident": "RES-0001",
            "unit": "UNIT-101",
            "access_granted": True,
            "method": "QR Code"
        }
        response = client.post("/api/v1/webhooks/access-log", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "received"
