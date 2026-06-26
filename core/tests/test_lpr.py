"""Unit tests for routers/lpr.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestLPR:
    def test_create_lpr_event(self, client):
        resp = client.post("/api/v1/lpr/", json={
            "plate_number": "ABC 1234",
            "direction": "entry",
            "confidence": 0.95,
            "parking_slot": "P1-23",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["plate_number"] == "ABC 1234"
        assert data["direction"] == "entry"
        assert data["confidence"] == 0.95
        assert data["is_visitor"] is True

    def test_create_lpr_event_exit(self, client):
        resp = client.post("/api/v1/lpr/", json={
            "plate_number": "XYZ 9999",
            "direction": "exit",
            "confidence": 0.88,
        })
        assert resp.status_code == 201
        assert resp.json()["direction"] == "exit"

    def test_list_lpr_events(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/lpr/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_lpr_events_filter_direction(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/lpr/?direction=entry", headers=headers)
        assert resp.status_code == 200

    def test_list_lpr_events_filter_visitor(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/lpr/?is_visitor=true", headers=headers)
        assert resp.status_code == 200

    def test_list_lpr_events_filter_plate(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/lpr/?plate_number=ABC", headers=headers)
        assert resp.status_code == 200

    def test_get_lpr_event(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/lpr/", json={
            "plate_number": "GET 1234",
            "direction": "entry",
            "confidence": 0.9,
        })
        eid = create.json()["id"]
        resp = client.get(f"/api/v1/lpr/{eid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["plate_number"] == "GET 1234"

    def test_get_nonexistent_lpr_event(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/lpr/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_mark_stolen(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/lpr/", json={
            "plate_number": "STOLEN 999",
            "direction": "entry",
            "confidence": 0.92,
        })
        eid = create.json()["id"]
        resp = client.post(f"/api/v1/lpr/{eid}/mark-stolen", headers=headers)
        assert resp.status_code == 200
        assert "stolen" in resp.json()["message"].lower()

        # Verify the event is now marked as stolen
        get_resp = client.get(f"/api/v1/lpr/{eid}", headers=headers)
        assert get_resp.json()["is_stolen_alert"] is True

    def test_mark_stolen_nonexistent(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post(f"/api/v1/lpr/{uuid4()}/mark-stolen", headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_mark_stolen(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/lpr/", json={
            "plate_number": "RES 1234",
            "direction": "entry",
            "confidence": 0.85,
        })
        eid = create.json()["id"]
        resp = client.post(f"/api/v1/lpr/{eid}/mark-stolen", headers=headers)
        assert resp.status_code == 403

    def test_unauthenticated_list_events(self, client):
        resp = client.get("/api/v1/lpr/")
        assert resp.status_code == 401
