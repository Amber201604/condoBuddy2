"""Unit tests for routers/users.py — user management."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestListUsers:
    def test_staff_can_list_users(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.get("/api/v1/users/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_staff_can_filter_by_role(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.get("/api/v1/users/?role=admin", headers=headers)
        assert resp.status_code == 200
        for user in resp.json():
            assert user["role"] == "admin"

    def test_resident_cannot_list_users(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/users/", headers=headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list(self, client):
        resp = client.get("/api/v1/users/")
        assert resp.status_code == 401


class TestGetUser:
    def test_staff_can_get_user(self, client, staff_auth, admin_auth):
        admin_id, _ = admin_auth
        _, headers = staff_auth
        resp = client.get(f"/api/v1/users/{admin_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(admin_id)

    def test_get_nonexistent_user(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.get(f"/api/v1/users/{uuid4()}", headers=headers)
        assert resp.status_code == 404


class TestCreateUser:
    def test_admin_can_create_user(self, client, admin_auth):
        _, headers = admin_auth
        resp = client.post("/api/v1/users/", json={
            "email": f"created-{uuid4().hex[:8]}@test.com",
            "password": "password123",
            "full_name": "Created User",
            "role": "resident",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "resident"

    def test_staff_cannot_create_user(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post("/api/v1/users/", json={
            "email": f"fail-{uuid4().hex[:8]}@test.com",
            "password": "password123",
            "full_name": "Fail User",
        }, headers=headers)
        assert resp.status_code == 403

    def test_create_duplicate_email(self, client, admin_auth):
        _, headers = admin_auth
        email = f"dupuser-{uuid4().hex[:8]}@test.com"
        client.post("/api/v1/users/", json={
            "email": email,
            "password": "password123",
            "full_name": "First",
        }, headers=headers)
        resp = client.post("/api/v1/users/", json={
            "email": email,
            "password": "password456",
            "full_name": "Second",
        }, headers=headers)
        assert resp.status_code == 400


class TestActivateUser:
    def test_admin_can_deactivate_user(self, client, admin_auth):
        _, headers = admin_auth
        # Create a user first
        create_resp = client.post("/api/v1/users/", json={
            "email": f"deactivate-{uuid4().hex[:8]}@test.com",
            "password": "password123",
            "full_name": "Deactivate User",
        }, headers=headers)
        user_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/v1/users/{user_id}/activate?active=false",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "deactivated" in resp.json()["message"]

    def test_admin_can_activate_user(self, client, admin_auth):
        _, headers = admin_auth
        create_resp = client.post("/api/v1/users/", json={
            "email": f"activate-{uuid4().hex[:8]}@test.com",
            "password": "password123",
            "full_name": "Activate User",
        }, headers=headers)
        user_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/v1/users/{user_id}/activate?active=true",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "activated" in resp.json()["message"]

    def test_activate_nonexistent_user(self, client, admin_auth):
        _, headers = admin_auth
        resp = client.patch(
            f"/api/v1/users/{uuid4()}/activate",
            headers=headers,
        )
        assert resp.status_code == 404


class TestGetMe:
    def test_get_me(self, client, resident_auth):
        uid, headers = resident_auth
        resp = client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(uid)
