"""Unit tests for routers/sensors.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestSensors:
    def test_staff_registers_sensor(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post("/api/v1/sensors/", json={
            "name": "Temp Sensor 1F",
            "sensor_type": "temperature",
            "location": "Hallway 1F",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Temp Sensor 1F"
        assert data["sensor_type"] == "temperature"

    def test_resident_cannot_register_sensor(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/sensors/", json={
            "name": "My Sensor",
            "sensor_type": "humidity",
            "location": "Unit 101",
        }, headers=headers)
        assert resp.status_code == 403

    def test_list_sensors(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/sensors/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_sensors_filter_type(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/sensors/?sensor_type=temperature", headers=headers)
        assert resp.status_code == 200

    def test_get_sensor(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/sensors/", json={
            "name": "Get Test Sensor",
            "sensor_type": "smoke",
            "location": "Stairwell A",
        }, headers=headers)
        sid = create.json()["id"]
        resp = client.get(f"/api/v1/sensors/{sid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test Sensor"

    def test_get_nonexistent_sensor(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/sensors/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_sensor_reading_normal(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/sensors/", json={
            "name": "Reading Normal Sensor",
            "sensor_type": "temperature",
            "location": "Lobby",
        }, headers=headers)
        sid = create.json()["id"]
        resp = client.post(f"/api/v1/sensors/{sid}/reading", json={
            "value": 22.5,
            "unit": "celsius",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "normal"

    def test_sensor_reading_smoke_alert(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/sensors/", json={
            "name": "Smoke Alert Sensor",
            "sensor_type": "smoke",
            "location": "Kitchen",
        }, headers=headers)
        sid = create.json()["id"]
        resp = client.post(f"/api/v1/sensors/{sid}/reading", json={
            "value": 80,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alert_triggered"
        assert "alert_id" in data

    def test_sensor_reading_water_leak_alert(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/sensors/", json={
            "name": "Water Leak Sensor",
            "sensor_type": "water_leak",
            "location": "Basement",
        }, headers=headers)
        sid = create.json()["id"]
        resp = client.post(f"/api/v1/sensors/{sid}/reading", json={
            "leak": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alert_triggered"

    def test_sensor_reading_high_temp_alert(self, client, staff_auth):
        _, headers = staff_auth
        create = client.post("/api/v1/sensors/", json={
            "name": "High Temp Sensor",
            "sensor_type": "temperature",
            "location": "Server Room",
        }, headers=headers)
        sid = create.json()["id"]
        resp = client.post(f"/api/v1/sensors/{sid}/reading", json={
            "value": 75,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alert_triggered"

    def test_sensor_reading_nonexistent(self, client):
        resp = client.post(f"/api/v1/sensors/{uuid4()}/reading", json={
            "value": 10.0,
        })
        assert resp.status_code == 404

    def test_unauthenticated_list_sensors(self, client):
        resp = client.get("/api/v1/sensors/")
        assert resp.status_code == 401

    def test_unauthenticated_create_sensor(self, client):
        resp = client.post("/api/v1/sensors/", json={
            "name": "Unauth Sensor",
            "sensor_type": "motion",
            "location": "Garage",
        })
        assert resp.status_code == 401
