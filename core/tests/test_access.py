"""Unit tests for routers/access.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestAccessLogs:
    def test_staff_creates_access_log(self, client, staff_auth, resident_auth):
        res_id, _ = resident_auth
        _, staff_headers = staff_auth
        resp = client.post("/api/v1/access/log", json={
            "user_id": str(res_id),
            "entry_point": "Main Entrance",
            "access_method": "nfc",
            "direction": "entry",
            "device_id": "NFC-001",
        }, headers=staff_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["entry_point"] == "Main Entrance"
        assert data["access_method"] == "nfc"
        assert data["direction"] == "entry"

    def test_resident_cannot_create_access_log(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/access/log", json={
            "entry_point": "Side Door",
            "access_method": "pin",
        }, headers=headers)
        assert resp.status_code == 403

    def test_list_access_logs(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/access/logs", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_access_logs_filter_entry_point(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.get("/api/v1/access/logs?entry_point=Main Entrance",
                         headers=headers)
        assert resp.status_code == 200

    def test_list_access_logs_filter_direction(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.get("/api/v1/access/logs?direction=entry",
                         headers=headers)
        assert resp.status_code == 200

    def test_resident_only_sees_own_logs(self, client, staff_auth, resident_auth):
        res_id, res_headers = resident_auth
        _, staff_headers = staff_auth
        # Create a log for resident
        client.post("/api/v1/access/log", json={
            "user_id": str(res_id),
            "entry_point": "Lobby",
            "access_method": "nfc",
        }, headers=staff_headers)
        # Create a log for another user
        client.post("/api/v1/access/log", json={
            "user_id": str(uuid4()),
            "entry_point": "Lobby",
            "access_method": "nfc",
        }, headers=staff_headers)
        # Resident should only see their own
        resp = client.get("/api/v1/access/logs", headers=res_headers)
        assert resp.status_code == 200
        logs = resp.json()
        for log in logs:
            if log["user_id"]:
                assert log["user_id"] == str(res_id)

    def test_grant_access_visitor_qr(self, client, resident_auth):
        _, headers = resident_auth
        # Create a visitor first to get an access code
        create_resp = client.post("/api/v1/visitors/", json={
            "visitor_name": "QR Test Visitor",
            "visit_date": "2026-07-10T14:00:00",
        }, headers=headers)
        access_code = create_resp.json()["access_code"]

        resp = client.post("/api/v1/access/grant", json={
            "method": "visitor_qr",
            "payload": access_code,
            "entry_point": "Main Gate",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "log_id" in data

    def test_grant_access_nfc(self, client):
        resp = client.post("/api/v1/access/grant", json={
            "method": "nfc",
            "payload": "CARD-12345",
            "entry_point": "Side Door",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "log_id" in data
        assert data["success"] is False  # simplified logic returns False for nfc

    def test_grant_access_pin(self, client):
        resp = client.post("/api/v1/access/grant", json={
            "method": "pin",
            "payload": "1234",
            "entry_point": "Garage",
        })
        assert resp.status_code == 200

    def test_access_log_with_extra_data(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post("/api/v1/access/log", json={
            "entry_point": "Loading Dock",
            "access_method": "manual",
            "direction": "entry",
            "extra_data": {"notes": "Delivery truck access"},
        }, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["extra_data"]["notes"] == "Delivery truck access"

    def test_unauthenticated_list_logs(self, client):
        resp = client.get("/api/v1/access/logs")
        assert resp.status_code == 401
