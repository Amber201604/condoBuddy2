"""Unit tests for routers/cameras.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestCameras:
    def test_staff_creates_camera(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post("/api/v1/cameras/", json={
            "name": "Lobby Camera",
            "location": "Main Lobby",
            "rtsp_url": "rtsp://192.168.1.10:554/stream1",
            "camera_type": "dome",
            "zone": "lobby",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Lobby Camera"
        assert data["camera_type"] == "dome"
        assert data["status"] == "offline"

    def test_resident_cannot_create_camera(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/cameras/", json={
            "name": "My Camera",
            "location": "Unit 101",
        }, headers=headers)
        assert resp.status_code == 403

    def test_list_cameras(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/cameras/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_cameras_filter_zone(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/cameras/?zone=lobby", headers=headers)
        assert resp.status_code == 200

    def test_list_cameras_filter_type(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/cameras/?camera_type=dome", headers=headers)
        assert resp.status_code == 200

    def test_get_camera(self, client, staff_auth, resident_auth):
        _, staff_headers = staff_auth
        _, res_headers = resident_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "Get Test Cam",
            "location": "Parking B1",
        }, headers=staff_headers)
        cam_id = create.json()["id"]
        resp = client.get(f"/api/v1/cameras/{cam_id}", headers=res_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test Cam"

    def test_get_nonexistent_camera(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/cameras/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_update_camera(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "Update Test Cam",
            "location": "Hallway 2F",
        }, headers=headers)
        cam_id = create.json()["id"]
        resp = client.patch(f"/api/v1/cameras/{cam_id}", json={
            "name": "Updated Camera Name",
            "status": "online",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Camera Name"
        assert resp.json()["status"] == "online"

    def test_update_nonexistent_camera(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.patch(f"/api/v1/cameras/{uuid4()}", json={
            "name": "Fail",
        }, headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_update_camera(self, client, staff_auth, resident_auth):
        _, staff_headers = staff_auth
        _, res_headers = resident_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "Res Update Test",
            "location": "Hallway 3F",
        }, headers=staff_headers)
        cam_id = create.json()["id"]
        resp = client.patch(f"/api/v1/cameras/{cam_id}", json={
            "name": "Should Fail",
        }, headers=res_headers)
        assert resp.status_code == 403

    def test_delete_camera(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "Delete Test Cam",
            "location": "Temp Location",
        }, headers=headers)
        cam_id = create.json()["id"]
        resp = client.delete(f"/api/v1/cameras/{cam_id}", headers=headers)
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_nonexistent_camera(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.delete(f"/api/v1/cameras/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_camera_stream(self, client, staff_auth, resident_auth):
        _, staff_headers = staff_auth
        _, res_headers = resident_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "Stream Test Cam",
            "location": "Pool Area",
        }, headers=staff_headers)
        cam_id = create.json()["id"]
        # Set stream_url via update (create doesn't save stream_url)
        client.patch(f"/api/v1/cameras/{cam_id}", json={
            "stream_url": "http://nvr/stream/pool",
        }, headers=staff_headers)
        resp = client.get(f"/api/v1/cameras/{cam_id}/stream", headers=res_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "stream_url" in data
        assert data["stream_url"] == "http://nvr/stream/pool"
        assert data["camera_name"] == "Stream Test Cam"

    def test_camera_stream_default_url(self, client, staff_auth, resident_auth):
        _, staff_headers = staff_auth
        _, res_headers = resident_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "No URL Cam",
            "location": "Garage",
        }, headers=staff_headers)
        cam_id = create.json()["id"]
        resp = client.get(f"/api/v1/cameras/{cam_id}/stream", headers=res_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "stream_url" in data
        assert f"http://nvr-connector:8001/stream/{cam_id}" == data["stream_url"]

    def test_camera_stream_nonexistent(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/cameras/{uuid4()}/stream", headers=headers)
        assert resp.status_code == 404

    def test_camera_heartbeat(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/cameras/", json={
            "name": "Heartbeat Test Cam",
            "location": "Gym",
        }, headers=headers)
        cam_id = create.json()["id"]
        resp = client.post(f"/api/v1/cameras/{cam_id}/heartbeat")
        assert resp.status_code == 200
        assert "heartbeat" in resp.json()["message"].lower()

        get_resp = client.get(f"/api/v1/cameras/{cam_id}", headers=headers)
        assert get_resp.json()["status"] == "online"

    def test_heartbeat_nonexistent(self, client):
        resp = client.post(f"/api/v1/cameras/{uuid4()}/heartbeat")
        assert resp.status_code == 404

    def test_unauthenticated_list_cameras(self, client):
        resp = client.get("/api/v1/cameras/")
        assert resp.status_code == 401
