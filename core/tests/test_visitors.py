"""Unit tests for routers/visitors.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestVisitors:
    def test_create_visitor(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/visitors/", json={
            "visitor_name": "John Guest",
            "visitor_phone": "555-1234",
            "visit_purpose": "Dinner",
            "visit_date": "2026-07-01T18:00:00",
            "expected_duration_minutes": 120,
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["visitor_name"] == "John Guest"
        assert data["access_code"] is not None
        assert len(data["access_code"]) == 6
        assert data["status"] == "scheduled"

    def test_list_visitors(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/visitors/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_visitors_filter_status(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/visitors/?status=scheduled", headers=headers)
        assert resp.status_code == 200

    def test_get_visitor(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/visitors/", json={
            "visitor_name": "Get Test Visitor",
            "visit_date": "2026-07-02T10:00:00",
        }, headers=headers)
        vid = create.json()["id"]
        resp = client.get(f"/api/v1/visitors/{vid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["visitor_name"] == "Get Test Visitor"

    def test_get_nonexistent_visitor(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/visitors/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_check_in_visitor(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/visitors/", json={
            "visitor_name": "Check In Visitor",
            "visit_date": "2026-07-03T14:00:00",
        }, headers=headers)
        vid = create.json()["id"]
        resp = client.post(f"/api/v1/visitors/{vid}/check-in", headers=headers)
        assert resp.status_code == 200
        assert "checked in" in resp.json()["message"]

        # Verify status changed
        get_resp = client.get(f"/api/v1/visitors/{vid}", headers=headers)
        assert get_resp.json()["status"] == "checked_in"

    def test_check_in_nonexistent(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post(f"/api/v1/visitors/{uuid4()}/check-in", headers=headers)
        assert resp.status_code == 404

    def test_check_out_visitor(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/visitors/", json={
            "visitor_name": "Check Out Visitor",
            "visit_date": "2026-07-04T14:00:00",
        }, headers=headers)
        vid = create.json()["id"]
        client.post(f"/api/v1/visitors/{vid}/check-in", headers=headers)
        resp = client.post(f"/api/v1/visitors/{vid}/check-out", headers=headers)
        assert resp.status_code == 200
        assert "checked out" in resp.json()["message"]

    def test_cancel_visitor(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/visitors/", json={
            "visitor_name": "Cancel Visitor",
            "visit_date": "2026-07-05T14:00:00",
        }, headers=headers)
        vid = create.json()["id"]
        resp = client.delete(f"/api/v1/visitors/{vid}", headers=headers)
        assert resp.status_code == 200
        assert "cancelled" in resp.json()["message"]

    def test_cancel_nonexistent(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.delete(f"/api/v1/visitors/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_see_others_visitor(self, client, resident_auth, staff_auth):
        _, staff_headers = staff_auth
        create = client.post("/api/v1/visitors/", json={
            "visitor_name": "Staff Visitor",
            "visit_date": "2026-07-06T14:00:00",
        }, headers=staff_headers)
        vid = create.json()["id"]

        _, res_headers = resident_auth
        resp = client.get(f"/api/v1/visitors/{vid}", headers=res_headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create(self, client):
        resp = client.post("/api/v1/visitors/", json={
            "visitor_name": "No Auth",
            "visit_date": "2026-07-07T14:00:00",
        })
        assert resp.status_code == 401
