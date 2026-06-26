"""Unit tests for routers/facility_booking.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestFacilityBooking:
    def test_create_booking(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Meeting Room A",
            "facility_type": "meeting_room",
            "start_time": "2026-08-01T10:00:00",
            "end_time": "2026-08-01T12:00:00",
            "notes": "Team meeting",
            "attendees_count": 5,
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["facility_name"] == "Meeting Room A"
        assert data["facility_type"] == "meeting_room"
        assert data["status"] == "pending"
        assert data["attendees_count"] == 5

    def test_create_booking_conflict(self, client, resident_auth):
        _, headers = resident_auth
        # First booking
        client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Party Room",
            "facility_type": "party_room",
            "start_time": "2026-09-01T14:00:00",
            "end_time": "2026-09-01T18:00:00",
        }, headers=headers)
        # Overlapping booking
        resp = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Party Room",
            "facility_type": "party_room",
            "start_time": "2026-09-01T16:00:00",
            "end_time": "2026-09-01T20:00:00",
        }, headers=headers)
        assert resp.status_code == 409
        assert "conflict" in resp.json()["detail"].lower()

    def test_create_booking_no_conflict_different_facility(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Gym",
            "facility_type": "gym",
            "start_time": "2026-09-01T14:00:00",
            "end_time": "2026-09-01T18:00:00",
        }, headers=headers)
        assert resp.status_code == 201

    def test_list_bookings(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/facility-bookings/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_bookings_filter_type(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/facility-bookings/?facility_type=meeting_room",
                         headers=headers)
        assert resp.status_code == 200

    def test_list_bookings_filter_status(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/facility-bookings/?status=pending",
                         headers=headers)
        assert resp.status_code == 200

    def test_get_booking(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Study Room 1",
            "facility_type": "study_room",
            "start_time": "2026-10-01T09:00:00",
            "end_time": "2026-10-01T11:00:00",
        }, headers=headers)
        bid = create.json()["id"]
        resp = client.get(f"/api/v1/facility-bookings/{bid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["facility_name"] == "Study Room 1"

    def test_get_nonexistent_booking(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/facility-bookings/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_see_others_booking(self, client, staff_auth, resident_auth):
        _, staff_headers = staff_auth
        create = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "BBQ Area",
            "facility_type": "bbq",
            "start_time": "2026-11-01T12:00:00",
            "end_time": "2026-11-01T15:00:00",
        }, headers=staff_headers)
        bid = create.json()["id"]
        _, res_headers = resident_auth
        resp = client.get(f"/api/v1/facility-bookings/{bid}", headers=res_headers)
        assert resp.status_code == 403

    def test_update_booking(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Game Room",
            "facility_type": "game_room",
            "start_time": "2026-12-01T14:00:00",
            "end_time": "2026-12-01T16:00:00",
            "attendees_count": 3,
        }, headers=headers)
        bid = create.json()["id"]
        resp = client.patch(f"/api/v1/facility-bookings/{bid}", json={
            "attendees_count": 6,
            "notes": "Updated notes",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["attendees_count"] == 6
        assert resp.json()["notes"] == "Updated notes"

    def test_update_nonexistent_booking(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.patch(f"/api/v1/facility-bookings/{uuid4()}", json={
            "notes": "Fail",
        }, headers=headers)
        assert resp.status_code == 404

    def test_cancel_booking(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Theatre",
            "facility_type": "theatre",
            "start_time": "2027-01-01T19:00:00",
            "end_time": "2027-01-01T22:00:00",
        }, headers=headers)
        bid = create.json()["id"]
        resp = client.delete(f"/api/v1/facility-bookings/{bid}", headers=headers)
        assert resp.status_code == 200
        assert "cancelled" in resp.json()["message"].lower()

    def test_cancel_nonexistent_booking(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.delete(f"/api/v1/facility-bookings/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_cancel_others_booking(self, client, staff_auth, resident_auth):
        _, staff_headers = staff_auth
        create = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Meeting Room B",
            "facility_type": "meeting_room",
            "start_time": "2027-02-01T10:00:00",
            "end_time": "2027-02-01T11:00:00",
        }, headers=staff_headers)
        bid = create.json()["id"]
        _, res_headers = resident_auth
        resp = client.delete(f"/api/v1/facility-bookings/{bid}", headers=res_headers)
        assert resp.status_code == 403

    def test_list_available_facilities(self, client):
        resp = client.get("/api/v1/facility-bookings/facilities/available")
        assert resp.status_code == 200
        data = resp.json()
        assert "facilities" in data
        assert len(data["facilities"]) > 0

    def test_list_available_facilities_filter_type(self, client):
        resp = client.get(
            "/api/v1/facility-bookings/facilities/available?facility_type=meeting_room"
        )
        assert resp.status_code == 200
        data = resp.json()
        for f in data["facilities"]:
            assert f["type"] == "meeting_room"

    def test_unauthenticated_create_booking(self, client):
        resp = client.post("/api/v1/facility-bookings/", json={
            "facility_name": "Gym",
            "facility_type": "gym",
            "start_time": "2027-03-01T10:00:00",
            "end_time": "2027-03-01T12:00:00",
        })
        assert resp.status_code == 401
