"""Unit tests for routers/work_orders.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from uuid import uuid4


class TestWorkOrders:
    def test_create_work_order(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/work-orders/", json={
            "title": "Fix leaking faucet",
            "description": "Kitchen faucet is dripping",
            "category": "maintenance",
            "priority": "high",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Fix leaking faucet"
        assert data["category"] == "maintenance"
        assert data["priority"] == "high"
        assert data["status"] == "open"

    def test_list_work_orders(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/work-orders/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_work_orders_filter_status(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/work-orders/?status=open", headers=headers)
        assert resp.status_code == 200

    def test_list_work_orders_filter_priority(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get("/api/v1/work-orders/?priority=high", headers=headers)
        assert resp.status_code == 200

    def test_get_work_order(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/work-orders/", json={
            "title": "Get test",
            "category": "cleaning",
        }, headers=headers)
        wo_id = create.json()["id"]
        resp = client.get(f"/api/v1/work-orders/{wo_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == wo_id

    def test_get_nonexistent_work_order(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.get(f"/api/v1/work-orders/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_update_work_order(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/work-orders/", json={
            "title": "Update test",
            "category": "maintenance",
        }, headers=headers)
        wo_id = create.json()["id"]
        resp = client.patch(f"/api/v1/work-orders/{wo_id}", json={
            "priority": "urgent",
            "status": "in_progress",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["priority"] == "urgent"
        assert resp.json()["status"] == "in_progress"

    def test_update_nonexistent(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.patch(f"/api/v1/work-orders/{uuid4()}", json={
            "status": "resolved",
        }, headers=headers)
        assert resp.status_code == 404

    def test_delete_work_order(self, client, resident_auth):
        _, headers = resident_auth
        create = client.post("/api/v1/work-orders/", json={
            "title": "Delete me",
            "category": "security",
        }, headers=headers)
        wo_id = create.json()["id"]
        resp = client.delete(f"/api/v1/work-orders/{wo_id}", headers=headers)
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"]

        # Verify it's gone
        resp2 = client.get(f"/api/v1/work-orders/{wo_id}", headers=headers)
        assert resp2.status_code == 404

    def test_delete_nonexistent(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.delete(f"/api/v1/work-orders/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_resident_cannot_see_others_work_order(self, client, resident_auth, staff_auth):
        """A resident can only view their own work orders."""
        res_id, res_headers = resident_auth
        staff_id, staff_headers = staff_auth

        # Staff creates a work order (acts as a different resident)
        create = client.post("/api/v1/work-orders/", json={
            "title": "Staff's WO",
            "category": "maintenance",
        }, headers=staff_headers)
        wo_id = create.json()["id"]

        # Resident tries to access it
        resp = client.get(f"/api/v1/work-orders/{wo_id}", headers=res_headers)
        assert resp.status_code == 403

    def test_staff_can_see_all_work_orders(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.get("/api/v1/work-orders/", headers=headers)
        assert resp.status_code == 200

    def test_unauthenticated_cannot_create(self, client):
        resp = client.post("/api/v1/work-orders/", json={
            "title": "No auth",
            "category": "maintenance",
        })
        assert resp.status_code == 401
