"""Unit tests for routers/notifications.py."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")


class TestNotifications:
    def test_register_push_token(self, client, resident_auth):
        uid, headers = resident_auth
        resp = client.post("/api/v1/notifications/register-push-token", json={
            "token": "fcm_token_abc123",
            "platform": "android",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Push token registered"
        assert data["user_id"] == str(uid)
        assert data["platform"] == "android"

    def test_register_push_token_ios(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/notifications/register-push-token", json={
            "token": "apns_token_xyz789",
            "platform": "ios",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["platform"] == "ios"

    def test_register_push_token_web(self, client, resident_auth):
        _, headers = resident_auth
        resp = client.post("/api/v1/notifications/register-push-token", json={
            "token": "web_push_token_456",
            "platform": "web",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["platform"] == "web"

    def test_register_push_token_unauthenticated(self, client):
        resp = client.post("/api/v1/notifications/register-push-token", json={
            "token": "no_auth_token",
            "platform": "android",
        })
        assert resp.status_code == 401

    def test_send_notification_to_user(self, client, resident_auth):
        uid, headers = resident_auth
        resp = client.post(
            "/api/v1/notifications/send",
            params={
                "title": "Test Alert",
                "body": "This is a test",
                "user_id": str(uid),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Notification sent"

    def test_send_notification_to_room(self, client, staff_auth):
        _, headers = staff_auth
        resp = client.post(
            "/api/v1/notifications/send",
            params={
                "title": "Staff Alert",
                "body": "Attention all staff",
                "room": "staff",
            },
            headers=headers,
        )
        assert resp.status_code == 200

    def test_send_notification_broadcast(self, client, admin_auth):
        _, headers = admin_auth
        resp = client.post(
            "/api/v1/notifications/send",
            params={
                "title": "Building Notice",
                "body": "Fire drill tomorrow at 10am",
            },
            headers=headers,
        )
        assert resp.status_code == 200

    def test_send_notification_unauthenticated(self, client):
        resp = client.post(
            "/api/v1/notifications/send",
            params={
                "title": "Unauthorized",
                "body": "Should fail",
            },
        )
        assert resp.status_code == 401

    def test_websocket_invalid_token(self, client):
        import pytest
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/v1/notifications/ws/invalid_token") as ws:
                pass

    def test_websocket_valid_connection(self, client, resident_auth):
        from app.core.security import create_access_token
        uid, _ = resident_auth
        token = create_access_token(data={"sub": str(uid)})
        with client.websocket_connect(f"/api/v1/notifications/ws/{token}") as ws:
            ws.send_json({"type": "ping"})
            resp = ws.receive_json()
            assert resp["type"] == "pong"
