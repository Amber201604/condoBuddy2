"""Unit tests for routers/packages.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestPackages:
    def test_staff_creates_package(self, client, staff_auth, resident_auth):
        res_id, _ = resident_auth
        _, staff_headers = staff_auth
        resp = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "tracking_number": "TRK123456",
            "carrier": "FedEx",
            "description": "Large box",
            "locker_code": "4567",
            "locker_number": "L-12",
        }, headers=staff_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tracking_number"] == "TRK123456"
        assert data["status"] == "received"
        assert data["locker_code"] == "4567"

    def test_resident_cannot_create_package(self, client, resident_auth):
        res_id, headers = resident_auth
        resp = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "description": "Small box",
        }, headers=headers)
        assert resp.status_code == 403

    def test_list_packages(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/packages/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_packages_filter_status(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/packages/?status=received", headers=headers)
        assert resp.status_code == 200

    def test_get_package(self, client, staff_auth, resident_auth):
        res_id, res_headers = resident_auth
        _, staff_headers = staff_auth
        create = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "description": "Get test",
        }, headers=staff_headers)
        pkg_id = create.json()["id"]
        resp = client.get(f"/api/v1/packages/{pkg_id}", headers=res_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == pkg_id

    def test_get_nonexistent_package(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/packages/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_pickup_package(self, client, staff_auth, resident_auth):
        res_id, res_headers = resident_auth
        _, staff_headers = staff_auth
        create = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "description": "Pickup test",
            "locker_code": "1234",
        }, headers=staff_headers)
        pkg_id = create.json()["id"]
        resp = client.post(f"/api/v1/packages/{pkg_id}/pickup", json={
            "access_code": "1234",
        }, headers=res_headers)
        assert resp.status_code == 200
        assert "picked up" in resp.json()["message"]

    def test_pickup_wrong_code(self, client, staff_auth, resident_auth):
        res_id, res_headers = resident_auth
        _, staff_headers = staff_auth
        create = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "description": "Wrong code test",
            "locker_code": "9999",
        }, headers=staff_headers)
        pkg_id = create.json()["id"]
        resp = client.post(f"/api/v1/packages/{pkg_id}/pickup", json={
            "access_code": "0000",
        }, headers=res_headers)
        assert resp.status_code == 400
        assert "Invalid access code" in resp.json()["detail"]

    def test_pickup_no_code_required(self, client, staff_auth, resident_auth):
        res_id, res_headers = resident_auth
        _, staff_headers = staff_auth
        create = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "description": "No code test",
        }, headers=staff_headers)
        pkg_id = create.json()["id"]
        resp = client.post(f"/api/v1/packages/{pkg_id}/pickup", json={},
                          headers=res_headers)
        assert resp.status_code == 200

    def test_pickup_nonexistent(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post(f"/api/v1/packages/{uuid4()}/pickup", json={},
                          headers=headers)
        assert resp.status_code == 404

    def test_notify_resident(self, client, staff_auth, resident_auth):
        res_id, _ = resident_auth
        _, staff_headers = staff_auth
        create = client.post("/api/v1/packages/", json={
            "resident_id": str(res_id),
            "description": "Notify test",
        }, headers=staff_headers)
        pkg_id = create.json()["id"]
        resp = client.post(f"/api/v1/packages/{pkg_id}/notify",
                          headers=staff_headers)
        assert resp.status_code == 200
        assert "notified" in resp.json()["message"].lower()

    def test_notify_nonexistent(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post(f"/api/v1/packages/{uuid4()}/notify", headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_see_others_package(self, client, staff_auth, resident_auth, admin_auth):
        admin_id, _ = admin_auth
        _, staff_headers = staff_auth
        _, res_headers = resident_auth
        create = client.post("/api/v1/packages/", json={
            "resident_id": str(admin_id),
            "description": "Admin's package",
        }, headers=staff_headers)
        pkg_id = create.json()["id"]
        resp = client.get(f"/api/v1/packages/{pkg_id}", headers=res_headers)
        assert resp.status_code == 403
